from datetime import date, timedelta
import requests
import pandas as pd

def bseindia_apiScraper(searchDate=None, qParams={}, prevData=None, depth=0):
    def cleanDate(sd):
        if not isinstance(sd, date):
            sd = str(sd).strip()
            try: sd  = date.fromisoformat(f'{sd[:4]}-{sd[4:6]}-{sd[6:]}')
            except: sd = date.today()
        return sd.isoformat().replace('-', '')
    
    isv = qParams.get('printMsgs', False)
    maxDepth = qParams.get('maxDepth', 998)
    prevData = prevData if prevData else []
    curPg = int(qParams.get('pageno', 1))
    curData, totalRows, totalPgs, t1Data = [], 0, 0, 'N/A'

    daysDict = {'week': 7, 'month': 30, 'year': 365, 'day': 1} # Added 'day': 1 for 24 hours
    searchDate = searchDate if searchDate else date.today()  
    if searchDate in daysDict: searchDate = daysDict[searchDate]
    if isinstance(searchDate, int) and searchDate > 0:
        prevDate = date.today() - timedelta(days=searchDate)
        qParams['strPrevDate'] = cleanDate(prevDate)
        qParams['strToDate'] = cleanDate(date.today()) 
    searchDate = cleanDate(searchDate) 

    qDefaults = {
        'pageno': 1, 'strCat': -1, 'strPrevDate': searchDate, 'strScrip': '', 
        'strSearch': 'P', 'strToDate': searchDate, 'strType': 'C'
    }
    qStr = [(k, qParams.get(k, v)) for k, v in qDefaults.items()]
    qStr = '&'.join([f'{qk}={qv}' for qk, qv in qStr])
    apiUrl = f'https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w?{qStr}'

    headers = {
        'authority': 'api.bseindia.com',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9,ms;q=0.8,ar;q=0.7',
        'origin': 'https://www.bseindia.com',
        'referer': 'https://www.bseindia.com/',
        'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }
    apiResp = requests.get(apiUrl, headers=headers)
    rMsg = f'{apiResp.status_code} {apiResp.reason} from {apiResp.url}'
    try:
        jData = apiResp.json()
        if not isinstance(jData.get('Table'), list): apiResp.raise_for_status()
        curData, t1Data = jData.get('Table', []), jData.get('Table1')
        if curData: totalPgs = curData[0].get('TotalPageCnt', 0) 
        status, msg = 'success', f'[page {curPg} of {totalPgs}] ' 
        msg += f'collected [{len(prevData)}+]{len(curData)} rows of data'
    except Exception as e:
        status, msg = 'error', f'{type(e)} {e}'
        if isv: print(f'Raw API Response (on error): {apiResp.text}') # Added for debugging
    if isv: print(f'[{depth}][{status}] {rMsg}\n{msg} from {apiUrl}')

    # retry same page [if request failed] or get next page #
    nextPg = None
    if depth < maxDepth: 
        if status == 'success' and curPg < totalPgs: nextPg = curPg + 1
        if status == 'error' and apiResp.status_code != 200:
            nextPg = curPg + int(len(curData) > 0)
    if nextPg:
        qParams['pageno'] = nextPg
        return bseindia_apiScraper(
            searchDate=searchDate, qParams=qParams, 
            prevData=prevData[:]+curData[:], depth=depth+1)
    
    ## return collected data ##
    if isinstance(t1Data,list) and len(t1Data)==1: t1Data = t1Data[0] 
    return {
        'data': prevData[:]+curData[:], 'Table1': t1Data, 'status': status, 
        'msg': msg, 'latest_call': apiUrl, 'latest_rStatus': rMsg, 
        'depth': depth, 'maxDepth': maxDepth, 'qParams': qParams
    }
