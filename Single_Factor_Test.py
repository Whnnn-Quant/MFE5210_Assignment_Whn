import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

import warnings
warnings.filterwarnings("ignore")

class Factor_Evaluation():

    def __init__(self,factor_name,direction):
        self.factor_name = factor_name
        self.direction = direction
        self.df_org_return = self.get_return_data()
        self.df_org_factor = self.get_factor_data(factor_name)
        self.df_return, self.df_factor = self.process_factor_return_data(self.df_org_return, self.df_org_factor)
        self.df_portfolio_return = self.calc_portfolio_ret(self.df_factor, self.df_return)
        
    def get_return_data(self):
        df_o2o_ret = pd.read_excel('Return_Data.xlsx',sheet_name='RtnsO2O',index_col=0)
        df_o2o_ret.index = pd.to_datetime(df_o2o_ret.index.astype(str))
        df_o2o_ret.columns = df_o2o_ret.columns.str.upper()

        df_o2o_ret_2 = df_o2o_ret.shift(-2).dropna(how='all')
        return df_o2o_ret_2
    
    def get_factor_data(self,factor_name):
        df_factor = pd.read_csv(f"Factor_csv/{factor_name}.csv",index_col=0)
        df_factor.index = pd.to_datetime(df_factor.index)
        df_factor = df_factor[df_factor.index<pd.to_datetime("2022-01-01")]
        return df_factor
    
    def process_factor_return_data(self,df_factor,df_return):
        futures_col = sorted(list(set(df_factor.columns).intersection(df_return.columns)))
        date_idx = sorted(list(set(df_factor.index).intersection(df_return.index)))

        df_factor = df_factor.loc[date_idx,futures_col]
        df_return = df_return.loc[date_idx,futures_col]

        return df_factor, df_return
    
    def calc_ic_plot(self):
        df_rankic = pd.DataFrame(index=self.df_factor.index,columns=['RankIC'])

        for date in self.df_factor.index.to_list():
            factor_array = np.array(self.df_factor.loc[date].fillna(0).values)
            return_array = np.array(self.df_return.loc[date].fillna(0).values)
            rankic, p_value = spearmanr(factor_array, return_array)
            df_rankic.loc[date,'RankIC'] = rankic
        
        fig = plt.figure(figsize=(15,6))
        plt.bar(df_rankic.index, df_rankic['RankIC'],color = 'darkred',width=10 )
        ax1 = plt.twinx()
        ax1.plot(df_rankic.cumsum(),color = 'orange')
        plt.grid()
        plt.title('RankIC = {}, RankIC_IR = {}'.format(round(df_rankic['RankIC'].mean(),4),round(df_rankic['RankIC'].mean()/df_rankic['RankIC'].std(),4)))
        plt.show()

    def calc_portfolio_ret(self, df_factor, df_return):

        df_portfolio_return = pd.DataFrame(index=df_factor.index, columns=['daily_return'])

        for date in df_factor.index.to_list():
            factor_array = np.array(df_factor.loc[date].fillna(0).values)
            return_array = np.array(df_return.loc[date].fillna(0).values)
            factor_position = self.direction * factor_array / np.sum(abs(factor_array))
            factor_return = factor_position * return_array
            total_return = np.sum(factor_return)

            df_portfolio_return.loc[date,'daily_return'] = total_return

        df_portfolio_return['cumsum_ret'] = df_portfolio_return['daily_return'].cumsum()
        
        return df_portfolio_return

    def plot_pnl(self):
        series = self.df_portfolio_return['daily_return']

        sharpe_ratio = series.mean() * np.sqrt(252) / series.std()
        cumsum_return = series.cumsum()

        cumsum_return.plot(figsize=(12,6),grid=True,title=f'Factor : {self.factor_name}, Sharpe : {round(sharpe_ratio,2)}')
        plt.show()

    def calculate_strategy_metrics(self):

        return_series = self.df_portfolio_return['daily_return']

        dates = pd.to_datetime(return_series.index.astype(str))
        returns = pd.Series(return_series.values, index=dates, name='daily_return')
        returns = returns.sort_index()
        
        grouped = returns.groupby(returns.index.year)
        
        metrics_df = pd.DataFrame(columns=['年化收益率', '年化夏普比率', '卡玛比率', '最大回撤', '偏度', '峰度'])
        
        for year, year_returns in grouped:
            if len(year_returns) < 1:
                continue  

            # 1. 年化收益率
            cumulative_return = year_returns.cumsum()
            annualized_return = year_returns.mean() * 252
            
            # 2. 年化波动率
            annualized_volatility = year_returns.std() * np.sqrt(252)
            
            # 3. 夏普比率（年化）
            sharpe_ratio = (annualized_return) / annualized_volatility
            
            # 4. 最大回撤
            cum_returns = (1 + year_returns).cumprod()
            peak = cum_returns.expanding(min_periods=1).max()
            drawdown = (peak - cum_returns) / peak
            max_drawdown = drawdown.max()
            
            # 5. 卡玛比率
            calmar_ratio = annualized_return / max_drawdown if max_drawdown != 0 else np.inf
            
            # 6. 偏度/峰度（基于日收益率）
            skewness = year_returns.skew()
            kurtosis = year_returns.kurtosis()
            
            metrics_df.loc[year] = [annualized_return,sharpe_ratio,calmar_ratio,max_drawdown,skewness,kurtosis]
        
        metrics_df = metrics_df.round({
            '年化收益率': 4,
            '年化夏普比率': 2,
            '卡玛比率': 2,
            '最大回撤': 4,
            '偏度': 2,
            '峰度': 2
        })
        
        return metrics_df