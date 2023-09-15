#!/usr/bin/env python3
import cgi
import cgitb
import json
import os
import requests
import statistics
import random
from datetime import date, timedelta
cgitb.enable()
print("Content-type: application/json\r\n\r\n")


def get_data_list_from_lambda():
    url = "https://j6bx1la7dh.execute-api.us-east-1.amazonaws.com/default/ReadS3Data"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data_list = response.json()
            return data_list
        else:
            print(f"Failed to retrieve data_list. Status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"Failed to retrieve data_list: {e}")

# Call the function to get the data_list
data_list = get_data_list_from_lambda()
form = cgi.FieldStorage()
minhistory = form.getvalue("h")
minhistory = int(minhistory) if minhistory.isdigit() else 0
shots = form.getvalue("d")
shots = int(shots) if shots.isdigit() else 0
signal = form.getvalue("t")
num_days =  form.getvalue("p")
num_days = int(num_days) if num_days.isdigit() else 0
def ec2_handler() :
    
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
results = ec2_handler()
ec2_result = {
    "status": "success",
    "result_dict": {
        "avgvar95": results[0][0],
        "avgvar99": results[0][1],
        "total_profit_loss":results[0][2],
            "dates" : results[0][3],
        "var95_list":results[0][4],
            "var99_list" : results[0][5],
        "profit_loss_list" : results[0][6]}
}
# Return the result as JSON data
print(json.dumps(ec2_result))


