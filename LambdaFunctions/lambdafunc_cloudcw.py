#!/usr/bin/env python3
import random
import boto3
import json
from datetime import datetime 
import statistics


s3_client = boto3.client('s3')
bucket_name = 'cloud6442385bk'
object_key = 'data_list.json'
response = s3_client.get_object(Bucket=bucket_name, Key=object_key) 
data_list = json.load(response['Body'])


def lambda_handler(event,context) :
    shots = int(event['key1'])
    minhistory = int(event['key2'])
    signal= event['key3']
    num_days =  int(event['key4'])
    
    var95_list = []
    var99_list = []
    dates = []
    results =[]
    profit_loss_list = []
    
    for i in range(minhistory, len(data_list)):
        if signal =='buy' and data_list[i]['Buy'] == 1: # if we’re interested in Buy signals
            close = [d['Close'] for d in data_list[i - minhistory:i]]
            return_val = [close[j] / close[j - 1] - 1 for j in range(1, len(close))]
            mean = statistics.mean(return_val)
            std = statistics.stdev(return_val)
            simulated = [random.gauss(mean, std) for _ in range(shots)]
            simulated.sort(reverse=True)
            var95 = simulated[int(len(simulated)*0.95)]
            var99 = simulated[int(len(simulated)*0.99)]
            var95_list.append(var95)
            var99_list.append((var99))
            dates.append(data_list[i]['Date'])
            avg_risk_var95 = sum(var95_list) / len(var95_list)
            avg_risk_var99 = sum(var99_list) / len(var99_list)
            
            if i + num_days < len(data_list):
                buy_price = data_list[i]['Close']
                sell_price = data_list[i + num_days]['Close']
                profit_loss = sell_price - buy_price
            else:
                profit_loss = 'N/A'
            profit_loss_list.append(profit_loss)
            
            
            
       
            
                
                
        elif signal =='sell' and data_list[i]['Sell'] == 1: # if we’re interested in Sell signals
            close = [d['Close'] for d in data_list[i - minhistory:i]]
            return_val = [close[j] / close[j - 1] - 1 for j in range(1, len(close))]
            mean = statistics.mean(return_val)
            std = statistics.stdev(return_val)
            simulated = [random.gauss(mean, std) for _ in range(shots)]
            simulated.sort(reverse=True)
            var95 = simulated[int(len(simulated)*0.05)]
            var99 = simulated[int(len(simulated)*0.01)]
            var95_list.append(var95)
            var99_list.append((var99))
            dates.append(data_list[i]['Date'])
            avg_risk_var95 = sum(var95_list) / len(var95_list)
            avg_risk_var99 = sum(var99_list) / len(var99_list)
            
            if i + num_days < len(data_list):
                sell_price = data_list[i]['Close']
                buy_price = data_list[i + num_days]['Close']
                profit_loss = buy_price - sell_price
            else:
                profit_loss = 'N/A'
            profit_loss_list.append(profit_loss)
            
            
         
    profit_loss_no_NA = [value for value in profit_loss_list if value != "N/A"]
    profit_loss = sum( profit_loss_no_NA )
    
    results.append((avg_risk_var95,avg_risk_var99 ,profit_loss,dates,var95_list,var99_list,profit_loss_no_NA ))
    return results
        
   
