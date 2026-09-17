"""Run with python -m supplyguard.pipeline; use --help for operational controls."""
import argparse
from contextlib import contextmanager
from dataclasses import asdict
from datetime import date
import json
import hashlib
import logging
import subprocess
import uuid
from dotenv import load_dotenv
from psycopg.types.json import Jsonb
from .config import ROOT,load_settings
from .database import get_connection
from .logging_config import configure_logging
from . import operations

LOGGER=logging.getLogger(__name__)
LOCK_ID=839104291
STAGES=['ingest','warehouse','model','forecast','publish']

@contextmanager
def stage(connection,run_id,name):
    LOGGER.info('Starting %s',name)
    connection.execute("INSERT INTO ops.pipeline_stage(run_id,stage,status) VALUES(%s,%s,'running')",(run_id,name))
    details={}
    try:
        yield details
    except BaseException:
        connection.execute("UPDATE ops.pipeline_stage SET status='failed',finished_at=now() WHERE run_id=%s AND stage=%s",(run_id,name))
        raise
    else:
        connection.execute("UPDATE ops.pipeline_stage SET status='success',finished_at=now(),details=%s WHERE run_id=%s AND stage=%s",(Jsonb(details),run_id,name))
        LOGGER.info('Completed %s: %s',name,json.dumps(details,default=str))

def run(settings,as_of=None,retrain=False,regenerate=False):
    load_dotenv(ROOT/'.env',override=False)
    run_id=uuid.uuid4()
    directory=ROOT/settings.artifact_dir/'runs'/str(run_id)
    directory.mkdir(parents=True)
    handler=logging.FileHandler(directory/'pipeline.log',encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
    logging.getLogger().addHandler(handler)
    connection=None
    registered=False
    try:
        connection=get_connection()
        connection.autocommit=True
        if not connection.execute('SELECT pg_try_advisory_lock(%s)',(LOCK_ID,)).fetchone()[0]:
            raise RuntimeError('Another SupplyGuard pipeline is running')
        operations.bootstrap(connection)
        revision=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=False).stdout.strip()
        dirty=subprocess.run(['git','status','--porcelain'],cwd=ROOT,capture_output=True,text=True,check=False).stdout.strip()
        # Abruptly killed previous runs are recoverable; the exclusive lock proves they are no longer active.
        connection.execute("UPDATE ops.pipeline_stage SET status='failed',finished_at=now() WHERE status='running'")
        connection.execute("UPDATE ops.pipeline_run SET status='failed',finished_at=now(),error='Interrupted before completion' WHERE status='running'")
        hashes={str(p.relative_to(ROOT)):operations.sha256(p) for base,pattern in [('src','*.py'),('sql','*.sql')] for p in sorted((ROOT/base).rglob(pattern))}
        (directory/'source_manifest.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
        execution={'requested_as_of':str(as_of) if as_of else None,'retrain':retrain,'regenerate_scenario':regenerate,
                   'code_sha256':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()}
        connection.execute("INSERT INTO ops.pipeline_run(run_id,status,config,code_revision) VALUES(%s,'running',%s,%s)",(run_id,Jsonb({**asdict(settings),'execution':execution}),revision+('-dirty' if dirty else '')))
        registered=True
        with stage(connection,run_id,'ingest') as details:
            details.update(operations.ingest_sources(connection))
        with stage(connection,run_id,'warehouse') as details:
            details.update(operations.warehouse(connection))
            latest=connection.execute('SELECT max(dt) FROM core.fact_daily_demand').fetchone()[0]
            as_of=as_of or latest
            if as_of is None or as_of>latest:
                raise ValueError('As-of date exceeds available observations')
            connection.execute('UPDATE ops.pipeline_run SET as_of_date=%s WHERE run_id=%s',(as_of,run_id))
        from .forecasting import fit_or_load,score
        with stage(connection,run_id,'model') as details:
            model,model_id,model_details=fit_or_load(connection,settings,as_of,retrain)
            details.update(model_details)
        with stage(connection,run_id,'forecast') as details:
            details.update(score(connection,model,model_id,settings,as_of,run_id))
        with stage(connection,run_id,'publish') as details:
            summary=operations.publish(connection,settings,as_of,run_id,model_id,regenerate)
            details.update(summary)
        result={'run_id':str(run_id),'status':'success','as_of_date':str(as_of),'model_id':model_id,**summary}
        (directory/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        return result
    except BaseException as error:
        if connection and registered and not connection.closed:
            # A post-publication logging failure must not relabel a committed snapshot as failed.
            connection.execute("UPDATE ops.pipeline_run SET status='failed',finished_at=now(),error=%s WHERE run_id=%s AND status='running'",(type(error).__name__+': '+str(error),run_id))
        LOGGER.exception('Pipeline failed; run_id=%s',run_id)
        raise
    finally:
        if connection:
            connection.close()  # Also releases the session advisory lock.
        logging.getLogger().removeHandler(handler)
        handler.close()

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',help='Path to pipeline TOML')
    parser.add_argument('--as-of',type=date.fromisoformat,help='Historical cutoff YYYY-MM-DD; default latest data date')
    parser.add_argument('--retrain',action='store_true',help='Create a fresh model artifact even if identical training inputs exist')
    parser.add_argument('--regenerate-scenario',action='store_true',help='Replace synthetic scenario inputs atomically during publication')
    parser.add_argument('--dry-run',action='store_true',help='Validate configuration and show stages without database writes')
    args=parser.parse_args(argv)
    configure_logging()
    settings=load_settings(args.config)
    if args.dry_run:
        print(json.dumps({'stages':STAGES,'config':asdict(settings),'as_of':str(args.as_of) if args.as_of else 'latest core date'},indent=2))
        return
    print(json.dumps(run(settings,args.as_of,args.retrain,args.regenerate_scenario),indent=2))

if __name__=='__main__':
    main()
