##Import data and clean it if nesseasary should see all 0
from Charts import SyntxDB
import numpy as np
import vectorbt as vbt
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier

def create_df():
    df = SyntxDB().add_equity('PLTR', start_time=20240615,end_time=20250608, resolution='minute')

    indexZeros = df[ df['Volume'] == 0 ].index

    df.drop(indexZeros , inplace=True)
    df.loc[(df["Volume"] == 0 )]
    df.isna().sum()
    """
    For this block createe a function that adds to the dataframe all the listed indicators, even allow me to add multiple windows of an indicator if needed
    """

    #add indicators and columns that might predict future trends

    df['ATR'] = vbt.ATR.run(df['High'], df['Low'], df['Close'], window=14).atr
    df['RSI'] = vbt.RSI.run(df['Close'], window=14).rsi
    df['Average'] = df['Close'].mean()
    df['MA40'] = vbt.MA.run(df['Close'],window=40).ma
    df['MA80'] = vbt.MA.run(df['Close'], window=80).ma
    df['MA160'] = vbt.MA.run(df['Close'],window=160).ma

    from scipy.stats import linregress
    def get_slope(array):
        y = np.array(array)
        x = np.arange(len(y))
        slope, intercept, r_value, p_value, std_err = linregress(x,y)
        return slope

    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    backrollingN = 6
    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    df['slopeMA40'] = df['MA40'].rolling(window=backrollingN).apply(get_slope, raw=True)
    df['slopeMA80'] = df['MA80'].rolling(window=backrollingN).apply(get_slope, raw=True)
    df['slopeMA160'] = df['MA160'].rolling(window=backrollingN).apply(get_slope, raw=True)
    df['AverageSlope'] = df['Average'].rolling(window=backrollingN).apply(get_slope, raw=True)
    df['RSISlope'] = df['RSI'].rolling(window=backrollingN).apply(get_slope, raw=True)

    #Targets quantifying down up or neither trends looking foward by n bars

    barsupfront = 10 #how many bars to look foward
    SLTPRatio = 1.2 #pipdiff/Ratio gives SL

    def mytarget(barsupfront, df1):
        length = len(df1)
        high = list(df1['High'])
        low = list(df1['Low'])
        close = list(df1['Close'])
        open = list(df1['Open'])
        atr = list(df1['ATR'])
        trendcat = [None] * length
        
        for line in range (0,length-barsupfront-2):
            valueOpenLow = 0
            valueOpenHigh = 0
            pipdiff = atr[line] *2
            for i in range(1,barsupfront+2):
                value1 = open[line+1]-low[line+i]
                value2 = open[line+1]-high[line+i]
                valueOpenLow = max(value1, valueOpenLow)
                valueOpenHigh = min(value2, valueOpenHigh)

                if ( (valueOpenLow >= pipdiff) and (-valueOpenHigh <= (pipdiff/SLTPRatio)) ):
                    trendcat[line] = 1 #-1 downtrend
                    break
                elif ( (valueOpenLow <= (pipdiff/SLTPRatio)) and (-valueOpenHigh >= pipdiff) ):
                    trendcat[line] = 2 # uptrend
                    break
                else:
                    trendcat[line] = 0 # no clear trend
                
        return trendcat

    df['mytarget'] = mytarget(barsupfront, df)
    print(f" Unclear: {(df['mytarget'] == 0).sum()} \n Downtrends:{(df['mytarget'] == 1).sum()} \n Uptrends: {(df['mytarget'] == 2).sum()}")
    return df








def create_test_model(df,attributes):
    # creating the data to be fed to the model
    df_model=df.dropna()

    X = df_model[attributes]
    y = df_model["mytarget"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)

    model = KNeighborsClassifier(n_neighbors=200, weights='uniform', algorithm='kd_tree', leaf_size=30, p=1, metric='minkowski', metric_params=None, n_jobs=1)
    model.fit(X_train, y_train)

    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)


    from sklearn.metrics import accuracy_score
    accuracy_train = accuracy_score(y_train, y_pred_train)
    accuracy_test = accuracy_score(y_test, y_pred_test)
    print("Accuracy train: %.2f%%" % (accuracy_train * 100.0))
    print("Accuracy test: %.2f%%" % (accuracy_test * 100.0))

    print(df_model['mytarget'].value_counts()*100/df_model['mytarget'].count())

    # Random Model, gambler?
    pred_test = np.random.choice([0, 1, 2], len(y_pred_test))
    accuracy_test = accuracy_score(y_test, pred_test)
    print("Accuracy Gambler: %.2f%%" % (accuracy_test * 100.0))

    ##MOre powerful model
    from xgboost import XGBClassifier
    model_xgb = XGBClassifier()
    model_xgb.fit(X_train, y_train)
    pred_train = model_xgb.predict(X_train)
    pred_test = model_xgb.predict(X_test)
    acc_train = accuracy_score(y_train, pred_train)
    acc_test = accuracy_score(y_test, pred_test)
    print('****Train Results****')
    print("Accuracy: {:.4%}".format(acc_train))
    print('****Test Results****')
    print("Accuracy: {:.4%}".format(acc_test))
    from matplotlib import pyplot
    from xgboost import plot_importance
    #plot feature importance
    plot_importance(model)
    pyplot.show()
    return df_model, model, model_xgb,
def backtest(df_model,model):
    # Predict over entire cleaned dataset
    df_model['prediction'] = model.predict(df_model[attributes])
    # Create signals based on prediction
    long_entries = (df_model['prediction'] == 2)
    short_entries = (df['prediction'] == 1)

    # Optional: hold for a fixed number of bars (barsupfront)
    barsupfront = 10
    long_exits = long_entries.shift(barsupfront).fillna(False)
    short_exits = short_entries.shift(barsupfront).fillna(False)
    # Create backtest using vectorbt
    pf = vbt.Portfolio.from_signals(
        close=df_model['Close'],
        entries=long_entries,
        exits=long_exits,
        short_entries=short_entries,
        short_exits=short_exits,
        size=1,  # you can customize position size
        fees=0.0005,  # 5bps per trade
        slippage=0.0002,
        freq='1min'
    )   
    return

if __name__ == "__main__":
    df = create_df()
    attributes = ['ATR', 'RSI', 'Average', 'MA40', 'MA80', 'MA160', 'slopeMA40', 'slopeMA80', 'slopeMA160', 'AverageSlope', 'RSISlope']
    df_model, model, model_xgb = create_test_model(df, attributes)
    # # Assuming the model is trained and available as `model`
    backtest(df, model)  # Uncomment this line to run backtest after training the model