#!/usr/bin/env python3
import yfinance as yf
import pandas as pd
from datetime import date, timedelta
from pandas_datareader import data as pdr
import logging 
import json
from flask import Flask ,request, jsonify , session
import time
import requests
import http.client
from concurrent.futures import ThreadPoolExecutor
import http.client
import urllib.parse


app = Flask(__name__)
app.secret_key = '6442385key'
global json_data
shots=None #initialise variable (shots)
history=None #initialise variable (history)
signal=None #initialise variable (signal)
days_after=None #initialise variable (profit)


def MonteCarlo():


        # override yfinance with pandas – seems to be a common step
    yf.pdr_override()

    # Get stock data from Yahoo Finance – here, asking for about 3 years
    today = date.today()
    decadeAgo = today - timedelta(days=1095)

    # Get stock data from Yahoo Finance – here, Gamestop which had an interesting 
    #time in 2021: https://en.wikipedia.org/wiki/GameStop_short_squeeze 

    data = pdr.get_data_yahoo('ZM', start=decadeAgo, end=today) 

    # Other symbols: TSLA – Tesla, AMZN – Amazon, ZM – Zoom, ETH-USD – Ethereum-Dollar etc.

    # Add two columns to this to allow for Buy and Sell signals
    # fill with zero
    data['Buy']=0
    data['Sell']=0


    # Find the signals – uncomment print statements if you want to 
    # look at the data these pick out in some another way
    # e.g. check that the date given is the end of the pattern claimed

    for i in range(2, len(data)): 

        body = 0.01

        # Three Soldiers
        if (data.Close[i] - data.Open[i]) >= body  \
    and data.Close[i] > data.Close[i-1]  \
    and (data.Close[i-1] - data.Open[i-1]) >= body  \
    and data.Close[i-1] > data.Close[i-2]  \
    and (data.Close[i-2] - data.Open[i-2]) >= body:
            data.at[data.index[i], 'Buy'] = 1
            #print("Buy at ", data.index[i])

        # Three Crows
        if (data.Open[i] - data.Close[i]) >= body  \
    and data.Close[i] < data.Close[i-1] \
    and (data.Open[i-1] - data.Close[i-1]) >= body  \
    and data.Close[i-1] < data.Close[i-2]  \
    and (data.Open[i-2] - data.Close[i-2]) >= body:
            data.at[data.index[i], 'Sell'] = 1
            #print("Sell at ", data.index[i])
    data.reset_index(inplace=True,drop=False)
    data_list = data.to_dict('records')
    for entry in data_list:
        entry['Date'] = entry['Date'].strftime('%Y-%m-%d')
        # convert data_list to JSON format
 
    global json_payload
    # Convert the JSON data to a JSON string
    json_payload = json.dumps(data_list)

    # URL of your Lambda function endpoint
    url = 'https://avgoq6d49c.execute-api.us-east-1.amazonaws.com/default/s3handler'

    # Payload with the key 'key1'
    payload = {'key1': json_payload}

    # Make a POST request to the Lambda function endpoint with the JSON payload
    requests.post(url, json=payload)
    return  # return nothing since this is a helper function
            

@app.route('/warmup', methods=['POST'])
def init():
    global runs
    global lambda_warmtime 
    global service
    global num_instances
    json_data = request.get_json()
    lambda_warmtime =0
    service = json_data.get("s")
    num_instances = json_data.get("r")
    res = requests.get('https://j6bx1la7dh.execute-api.us-east-1.amazonaws.com/default/LambdaFuncCheckEc2Resources')
    instance_data = res.json()
    num_instances_present = instance_data[2]
    MonteCarlo()## call the monte carlo function to store signal data in bucket   
    if service == "ec2" and int(num_instances_present) == 0: #Do this check in order to make sure user cant warm up new resources if resources are already available
        if request.method == 'POST':
                global startec2time
                startec2time = time.time()
                c = http.client.HTTPSConnection("j6bx1la7dh.execute-api.us-east-1.amazonaws.com")
                json= '{ "key1": "'+num_instances+'"}'
                c.request("POST", "/default/ec2handler", json)
                ecresponse = jsonify(result='ok')
                return ecresponse
    if service == "lambda": #if service is lambda 
        if request.method == 'POST':
            #initialise http connection to lambda host url
            warmup_url = http.client.HTTPSConnection("j6bx1la7dh.execute-api.us-east-1.amazonaws.com")
            start_lambdawarmup= time.time() # start record time for warmup
            #send a small request to the lambda function to prevent cold start
            warmup_json='{ "key1": ' + str(500) + ', "key2": ' + str(50) + ', "key3": "' + str('Buy') + '", "key4": "' + str(20) + '" }'
            warmup_url.request("POST", "/default/lambdafunc_cloudcw", warmup_json)
            lambda_warmtime = round(time.time() - start_lambdawarmup, 4)  # record warm up time
            lambdawarmresponse = jsonify(result='ok')
            return lambdawarmresponse
    else:
        return jsonify(result='invalid . Remember to terminate all instances before starting new ones')

@app.route('/resources_ready', methods=['GET'])
def resources_ready():
    global ip_list ,id_list
    global check_if_terminated

    if service=='ec2':
        try:
            # Make a GET request to the Lambda function
            response = requests.get('https://j6bx1la7dh.execute-api.us-east-1.amazonaws.com/default/LambdaFuncCheckEc2Resources')
            data = response.json()
            ip_list = data[0]
            id_list = data[1]
            num_instances_created = data[2]

            if int(num_instances) == int(num_instances_created): #make sure instances created matches with num of instances requested
      
                check_if_terminated = False
                return jsonify(warm='true')

            else:
                check_if_terminated = True
                return jsonify(warm='false'), response.status_code
            

        except requests.exceptions.RequestException as e:
            # Handle request exceptions 
            return jsonify(warm ='false'), 500



    if service == 'lambda':

        warm_lambda = lambda_warmtime > 0  
        return jsonify(warm=warm_lambda)

    else:
        return jsonify(warm=False)
    
@app.route('/get_warmup_cost', methods=['GET'])
def get_warmup_cost():
    if service == 'lambda':
        lambdawarm_cost =  round(lambda_warmtime * 1000 * 0.0000000083 ,6) #calcualte lambda costs
        return jsonify(billable_time = f"{lambda_warmtime} Seconds" , cost= f"${lambdawarm_cost}" )
    if service == 'ec2':
        rate_per_hour = 0.0116 #t2micro hourly cost
        seconds_in_an_hour = 3600  # 1 hour has 3600 seconds
        # Calculate the rate per second
        rate_per_second = rate_per_hour / seconds_in_an_hour
        # assuming warmup takes approximately 30 seconds
        time_in_seconds = 30 
        # Calculate the cost for 30 seconds
        ec2warm_cost = rate_per_second * time_in_seconds * int(num_instances) 
        return jsonify(billable_time = "30 Seconds", cost= f"${ec2warm_cost}"  )
    else:
        return jsonify(billable_time = "invalid", cost= "invalid")

def ip_to_url(ip):
    ip_with_dashes = ip.replace('.', '-')
    url = f"https://ec2-{ip_with_dashes}.compute-1.amazonaws.com/"
    return {'resource': url}

@app.route('/get_endpoints', methods=['GET'])
def get_endpoints():
    if service == 'lambda':
        lambda_url = "https://j6bx1la7dh.execute-api.us-east-1.amazonaws.com/default/lambdafunc_cloudcw"
        return jsonify(resource = lambda_url) 
    if service == 'ec2':
        ip_urls = [ip_to_url(ip) for ip in ip_list]
        ips_json = json.dumps(ip_urls)

        return jsonify(ips_json)
    else:
        return jsonify(resource = "invalid") 


#function for sending requests to the lamda function
def getpage(id):
    try:
        host = "j6bx1la7dh.execute-api.us-east-1.amazonaws.com" #lambda host url
        c = http.client.HTTPSConnection(host)  #initialise http connection to lambda host url
        json_values = '{ "key1": ' + str(shots) + ', "key2": ' + str(history) + ', "key3": "' + str(signal) + '", "key4": "' + str(days_after) + '" }'  #user inputs to be used as payload
        
        c.request("POST", "/default/lambdafunc_cloudcw", json_values ) #send post request to specified endpoint
        response = c.getresponse() #get response and save in variable
        data = response.read().decode('utf-8')  #decode response into string using UTF-8 encoding
        data_list = json.loads(data)#parse the json encoded string and convert to python object
        return data_list
    except IOError: # throw error if host url isnt available
        print('Failed to open ', host) # Is the Lambda address correct?
    return str(id)
#function to run the get page function concurrently using thread pool executor for each element in the runs list
def getpages():
    with ThreadPoolExecutor() as executor:
        runs=[value for value in range(int(num_instances))]#define parralel rund based on number of resources requested  
        results = list(executor.map(getpage, runs)) #store results of each parralel run
    return results #return results




@app.route('/analyse', methods=['POST'])
def analyse():
    json_data = request.get_json()
    global results_ec2calc ,results_lambdacalc
    global shots ,history ,signal ,days_after
    global lambdacalc_time
    global success_data
    global reset
    reset = False
    history= json_data.get("h")
    shots= json_data.get("d")
    signal = json_data.get("t")
    days_after = json_data.get("p")
    if service == 'lambda':
        start = time.time()
        results_lambdacalc= getpages() #run getpages and get the results 
          # Storing in the calculations list
        calculations = session.get('calculations', [])
        calculations.append({'s':service, 'r': num_instances,'h': history , 'd' : shots , 't':signal , 'p' : days_after})
        session['calculations'] = calculations
        lambdacalc_time = time.time() - start
        return jsonify(result = 'ok') 

    if service == 'ec2' and not check_if_terminated:
        def send_request(url): #nested function which sends the request to the instance url with the specified payload
            history= json_data.get("h")
            shots= json_data.get("d")
            signal = json_data.get("t")
            days_after = json_data.get("p")
            payload = { #get user input and save as payload to be used
                    'h': int(history),
                    'd':int(shots),
                    't': signal,
                    'p': int(days_after)
                }
            response = requests.post(url, data=payload)
            return response.json()

        global ec2calctime
        startec2calctime = time.time()
        #Call thread pool executor to execute the send request function concurrently
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(send_request, f'http://{ip}/ec2_script.py') for ip in ip_list]
            results_ec2calc = [future.result() for future in futures]
        ec2calctime = time.time() - startec2calctime
          # Storing in the calculations list
        calculations = session.get('calculations', [])
        calculations.append({'s':service, 'r': num_instances,'h': history , 'd' : shots , 't':signal , 'p' : days_after})
        session['calculations'] = calculations
        success_data = [entry['result_dict'] for entry in results_ec2calc if entry['status'] == 'success']
        return jsonify(result ='ok')
    
    else:
        return jsonify("invalid . This could mean resources have been terminated(EC2)") 


@app.route('/get_sig_vars9599', methods=['GET'])
def get_sig_vars9599():
    global var95_averages 
    global var99_averages 
    if service == 'lambda' and not reset:  #return output if session isnt empty 
        var95_list =[]
        var99_list =[]
        for nested_list in results_lambdacalc:

            # Extract the 4th element of the nested list and append it to var95 list
            var95_list .append(nested_list[0][4])
            # Extract the 5th element of the nested list and append it to var99 list
            var99_list.append(nested_list[0][5])
        transposed_var95= list(zip(*var95_list)) #transpose var95 list
        # calculate average of each element
        var95_averages = [sum(x)/len(x) for x in transposed_var95] # calculate average of var95 transposed 
        transposed_var99= list(zip(*var99_list))  #transpose var99 list
       # calculate average of var99 transposed 
        var99_averages = [sum(x)/len(x) for x in transposed_var99]
        var_result_dict = {
        "var95": var95_averages[:20],  
        "var99": var99_averages[:20] 
    }
        return jsonify(var_result_dict) 
    if service == 'ec2' and not reset and not check_if_terminated: #return output if session isnt empty and instances arent terminated
        var95_values = [] #create list to store var95 values
        var99_values = [] #create list to store var99 values
        for data in success_data:
            # Extract the 'var95_list' values from the current dictionary
            var95_list = data['var95_list']
            # Append the values to the var95_values list
            var95_values.append(var95_list)
            var99_list = data['var99_list']
            # Append the values to the var95_values list
            var99_values.append(var99_list)
        # Transpose the var95/99_values list to group the values by index
        transposed_var_95_list = list(map(list, zip(*var95_values)))
        transposed_var_99_list = list(map(list, zip(*var99_values)))
            # Calculate the averages for the var95/99_values list
        var95_averages  = [sum(values) / len(values) for values in  transposed_var_95_list ]
        var99_averages  = [sum(values) / len(values) for values in  transposed_var_99_list ]
        var_result_dict = {
        "var95": var95_averages[:20],  
        "var99": var99_averages[:20] 
    }
        return jsonify(var_result_dict) 
    else:
        return jsonify("No Results Available . Analysis Was Reset or Instances Terminated(EC2) ") 

@app.route('/get_avg_vars9599', methods=['GET'])
def get_avg_vars9599():
    global var95_avg
    global var99_avg
    if service == 'lambda' and not reset: #return output if session isnt empty
        var_avg_list= []
        for sublist in results_lambdacalc:
            var_list = sublist[0][:2] #retreive the first two elements of each sublist
            var_avg_list.append(var_list)
        transposed_var_list= list(zip(*var_avg_list))  # transpose the  list
        var_averages = [sum(x)/len(x) for x in transposed_var_list] #get the averages of the list
        var95_avg = round(var_averages[0], 4)
        var99_avg = round(var_averages[1], 4)
        calculations = session.get('calculations', [])
        calculations[-1]['avg95'] = var95_avg # Update the last dictionary
        calculations[-1]['avg99'] = var99_avg # Update the last dictionary
        session['calculations'] = calculations
        var_averages_dict = {
         "var95": var95_avg,  
         "var99": var99_avg  
    }
        return jsonify(var_averages_dict) 
    
    if service == 'ec2' and not reset and not check_if_terminated: #return output if session isnt empty and instances arent terminated
        # Transpose the data to group 'avg_risk_var95'  and  'avg_risk_var99' values together
        transposed_var = list(zip(*[(entry['avgvar95'], entry['avgvar99']) for entry in success_data]))
        average_var= [sum(sublist) / len(sublist) for sublist in transposed_var]
        var95_avg = round(average_var[0],4) #round var95 to 4 d.p
        var99_avg = round(average_var[1],4)#round var99 to 4 d.p
        calculations = session.get('calculations', [])
        calculations[-1]['avg95'] = var95_avg # Update the last dictionary
        calculations[-1]['avg99'] = var99_avg # Update the last dictionary
        session['calculations'] = calculations
        var_avg_dict = {
         "var95": var95_avg,  
         "var99": var99_avg  
    }
        return jsonify(var_avg_dict) 
    else:
        return jsonify("No Results Available . Analysis Was Reset or Instances Terminated(EC2) ") 
 

@app.route('/get_sig_profit_loss', methods=['GET'])
def get_sig_profit_loss():
    if service == 'lambda' and not reset: #return output if session isnt empty
        
        profitloss_list = []
        for nested_list in results_lambdacalc:

            # Extract the 6th element of the nested list and append it to var95 list
             profitloss_list.append(nested_list[0][6])
        transposed_profitloss= list(zip(*profitloss_list)) #transpose var95 list
        # calculate average of each element
        profitloss_averages = [sum(x)/len(x) for x in transposed_profitloss] # calculate average of var95 transposed 
        profitloss_result_dict = {
        "profit_loss": profitloss_averages [-20:]
    }
        return jsonify(profitloss_result_dict) 
    if service == 'ec2' and not reset and not check_if_terminated: #return output if session isnt empty and instances arent terminated
        profit_loss_values =[] #create list to store profit/loss values
        for data in success_data:
            # Extract the profit_loss  values 
            profit_loss_list = data['profit_loss_list']
            # Append the values to the profit_loss  list
            profit_loss_values.append(profit_loss_list)
        # Transpose the profit loss list
        transposed_profit_loss_list = list(map(list, zip(*profit_loss_values)))
        averages_profit_loss_list = ['$' + str(round(sum(values) / len(values), 2)) for values in transposed_profit_loss_list] # Calculate the averages for the profit loss list
        profitloss_result_dict = {
        "profit_loss":  averages_profit_loss_list[-20:]
    }
        return jsonify(profitloss_result_dict) 
    else:
        return jsonify("No Results Available . Analysis Was Reset or Instances Terminated(EC2) ") 


@app.route('/get_tot_profit_loss', methods=['GET'])
def get_tot_profit_loss():
    global total_profit_loss
    if service == 'lambda' and not reset: #return output if session isnt empty 
        profitloss_list = []
        for nested_list in results_lambdacalc:

            # Extract the 6th element of the nested list and append it to var95 list
             profitloss_list.append(nested_list[0][6])
        transposed_profitloss= list(zip(*profitloss_list)) #transpose var95 list
        # calculate average of each element
        profitloss_averages = [sum(x)/len(x) for x in transposed_profitloss] # calculate average of var95 transposed 
        total_profit_loss = sum(profitloss_averages)
        calculations = session.get('calculations', [])
        calculations[-1]['profit_loss'] = total_profit_loss# Update the last dictionary
        session['calculations'] = calculations
        total_profitloss_result_dict = {
        "profit_loss": total_profit_loss
    }
        return jsonify(total_profitloss_result_dict ) 
    if service == 'ec2' and not reset and not check_if_terminated: #return output if session isnt empty and instances arent terminated
        transposed_profit_loss_total = [entry['total_profit_loss'] for entry in success_data]
        # Calculate the average of the 'total_profit_loss' values
        average_profit_loss_total = sum(transposed_profit_loss_total) / len(transposed_profit_loss_total)
        # Round the average to 4 decimal places
        total_profit_loss = round(average_profit_loss_total, 4)
        calculations = session.get('calculations', [])
        calculations[-1]['profit_loss'] = total_profit_loss# Update the last dictionary
        session['calculations'] = calculations
        total_profitloss_dict = {"profit_loss": total_profit_loss}
        return jsonify(total_profitloss_dict ) 
    else:
        return jsonify("No Results Available . Analysis Was Reset or Instances Terminated(EC2) ") 


@app.route('/get_chart_url', methods=['GET'])
def get_chart_url():
    if service == 'lambda' and not reset: #return output if session isnt empty
        dates_list =[]
        for nested_list in results_lambdacalc:
            # Extract the 3rd element of the nested list and append it to dates listlist
            dates_list.append(nested_list[0][3])
        dates= dates_list[0] #retrieve the first dates list since all dates are same across threads
        data1 = [round(x, 3) for x in  var95_averages] #round to 3 decimal places
        data2 = [round(x, 3) for x in  var99_averages] #round to 3 decimal places

        data1_str = [str(x) for x in data1]  #convert list items to string
        data2_str = [str(x) for x in data2]  #convert list items to string
        dateIDs =  list(range(1, len(dates) + 1))
        dateID =  [str(x) for x in dateIDs] #create date ids list for corresponding dates
        
        var95_str = ','.join([str(var95_avg)] * len(data1))  #create comma seperated string
        var99_str = ','.join([str(var99_avg)] * len(data2))  #create comma seperated string
        #url template for chart generation using image charts
        url_template = 'https://image-charts.com/chart?cht=lc&chd=t:{data1}|{data2}|{var95_str}|{var99_str}&chs=600x400&chxt=x,y&chxl=0:|&chco=9CFF33,33C1FF&chds=a&chdl=var95|var99|avg95|avg99'
        #build chart url from url template
        chart_url = url_template.format(data1=','.join(data1_str), data2=','.join(data2_str), dateID='|'.join(map(urllib.parse.quote,dateID)), var95_str=var95_str, var99_str=var99_str)

       
        return jsonify(url = chart_url ) 
    if service == 'ec2' and not reset and not check_if_terminated: #return output if session isnt empty and instances arent terminated
        dates = success_data[0]['dates']
        data1 = [round(x, 3) for x in var95_averages] #round to 3 decimal places
        data2 = [round(x, 3) for x in var99_averages] #round to 3 decimal places

        data1_str = [str(x) for x in data1]  #convert list items to string
        data2_str = [str(x) for x in data2]  #convert list items to string
        dateIDs =  list(range(1, len(dates) + 1))
        dateID =  [str(x) for x in dateIDs] #create date ids list for corresponding dates
        
        var95_str = ','.join([str(var95_avg)] * len(data1))  #create comma seperated string
        var99_str = ','.join([str(var99_avg)] * len(data2))  #create comma seperated string
        #url template for chart generation using image charts
        url_template = 'https://image-charts.com/chart?cht=lc&chd=t:{data1}|{data2}|{var95_str}|{var99_str}&chs=600x400&chxt=x,y&chxl=0:|&chco=9CFF33,33C1FF&chds=a&chdl=var95|var99|avg95|avg99'
        #build chart url from url template
        chart_url = url_template.format(data1=','.join(data1_str), data2=','.join(data2_str), dateID='|'.join(map(urllib.parse.quote,dateID)), var95_str=var95_str, var99_str=var99_str)
        return jsonify(url = chart_url ) 
    else:
        return jsonify("No Results Available . Analysis Was Reset or Instances Terminated(EC2) ") 


@app.route('/get_time_cost', methods=['GET'])
def get_time_cost():
    if service == 'lambda' and not reset: #return output if session isnt empty
        global lambdarun_cost
        lambdarun_cost =  round(lambdacalc_time * 1000 * 0.0000000083 * int(num_instances),6)
        calculations = session.get('calculations', [])
        calculations[-1]['time'] = lambdacalc_time # Update the last dictionary
        calculations[-1]['cost'] = lambdarun_cost # Update the last dictionary
        session['calculations'] = calculations
        return jsonify(time = lambdacalc_time ,cost = lambdarun_cost )
    if service == 'ec2' and not reset and not check_if_terminated: #return output if session isnt empty and instances arent terminated
        global ec2_time , ec2_cost
        rate_per_hour = 0.0116 #t2micro hourly cost
        seconds_in_an_hour = 3600  # 1 hour has 3600 seconds
        # Calculate the rate per second
        rate_per_second = rate_per_hour / seconds_in_an_hour
        # Calculate the cost
        ec2_time = time.time() - startec2time 
        ec2_cost = rate_per_second *  ec2_time * int(num_instances) 
        calculations = session.get('calculations', [])
        calculations[-1]['time'] = ec2calctime # Update the last dictionary
        calculations[-1]['cost'] = ec2_cost # Update the last dictionary
        session['calculations'] = calculations
        return jsonify(time = ec2calctime ,cost = ec2_cost ) 
    else:
        return jsonify("No Results Available . Analysis Was Reset or Instances Terminated(EC2) ") 
   
 

@app.route('/get_audit', methods=['GET'])
def get_audit():
    if service == 'lambda':
        calculations = session.get('calculations', [])
        return jsonify({'results': calculations})
 
    if service == 'ec2' and not check_if_terminated:
        calculations = session.get('calculations', [])
        return jsonify({'results': calculations})
 
    else:
        return jsonify("No Results Available . Analysis Was Reset or Instances Terminated(EC2) ") 

@app.route('/reset', methods=['GET'])
def reset():
    global reset
    session.clear()
    reset = True
    return jsonify(result = 'ok' )



@app.route('/terminate', methods=['GET'])
def terminate():
    if service == 'ec2':
        delete_url = "https://j6bx1la7dh.execute-api.us-east-1.amazonaws.com/default/DeleteEc2Instances"
        requests.get(delete_url)
        return jsonify(result = 'ok' )
    else:
        return jsonify("invalid . are you currently using lambda?") 




@app.route('/resources_terminated', methods=['GET'])
def resources_terminated():
    if service == 'ec2':
        global check_if_terminated
        check_terminate_url = "https://j6bx1la7dh.execute-api.us-east-1.amazonaws.com/default/CheckRunningInstances"
        check_terminateresponse = requests.get(check_terminate_url)
        check_if_terminated= check_terminateresponse.json()
        return jsonify(terminated= check_if_terminated )
    else:
        return jsonify("invalid") 

if __name__ == '__main__': 
    # Entry point for running on the local machine 
    # On GAE, endpoints (e.g. /) would be called. 
    # Called as: gunicorn -b :$PORT index:app, 
    # host is localhost; port is 8080; this file is index (.py) 
    app.run(host='127.0.0.1', port=5000, debug=True)
