from datetime import date
import numpy as np
import pandas as pd
import pytest
from supplyguard.config import Settings
from supplyguard.forecasting import build_forward_features

def history():
    return pd.DataFrame({'store_id':1,'product_id':2,'dt':pd.date_range('2024-06-05',periods=28),
        'sale_amount':np.arange(1,29,dtype=float),'stockout_hours':0,
        'discount':.9,'activity_flag':1,'first_category_id':3,'second_category_id':4,'third_category_id':5})

def test_forward_features_use_cutoff_not_target_actual():
    data=history()
    future=data.iloc[[-1]].copy()
    future['dt']=pd.Timestamp('2024-07-03')
    future['sale_amount']=999999
    row=build_forward_features(pd.concat([data,future]),date(2024,7,2)).iloc[0]
    assert row.sales_lag_1==28
    assert row.sales_lag_7==22
    assert row.sales_rolling_mean_7==25
    assert row.sales_rolling_mean_28==14.5
    assert row.sales_rolling_std_7==pytest.approx(np.std(np.arange(22,29),ddof=1))
    assert row.day_of_week==3
    assert row.discount==.9

def test_forward_features_reject_gaps_and_duplicates():
    data=history()
    with pytest.raises(ValueError,match='28 consecutive'):
        build_forward_features(data.iloc[1:],date(2024,7,2))
    with pytest.raises(ValueError,match='Duplicate'):
        build_forward_features(pd.concat([data,data.iloc[[-1]]]),date(2024,7,2))

@pytest.mark.parametrize('budget',[-1,float('nan'),float('inf')])
def test_invalid_budget_rejected(budget):
    with pytest.raises(ValueError):
        Settings(budget=budget)

def test_zero_budget_allowed_and_weights_checked():
    assert Settings(budget=0).budget==0
    with pytest.raises(ValueError,match='weights'):
        Settings(weights={'coverage':1})

def test_artifact_path_cannot_escape_project():
    with pytest.raises(ValueError,match='subdirectory'):
        Settings(artifact_dir='../elsewhere')
