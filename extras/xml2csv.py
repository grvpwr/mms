import os
import xml.etree.ElementTree as ET
import zipfile
import csv
from datetime import datetime, date
from decimal import Decimal

# os.chdir(r'D:\Out mandates\2025-01-17')

def xml2dict(f):
    tree = ET.parse(f)
    
    root = tree.getroot()
    ns = {'ns': 'urn:iso:std:iso:20022:tech:xsd:pain.012.001.01'}
    dict = {}
    
    try:
        dict['AcqMsgId'] = root.find('./ns:MndtAccptncRpt/ns:GrpHdr/ns:MsgId', ns).text
    except AttributeError:
        pass
    
    try:
        dict['AcqCreDtTm'] = datetime.fromisoformat(root.find('./ns:MndtAccptncRpt/ns:GrpHdr/ns:CreDtTm', ns).text)
    except AttributeError:
        pass
    
    try:
        dict['OriginalMsgId'] = root.find('./ns:MndtAccptncRpt/ns:UndrlygAccptncDtls/ns:OrgnlMsgInf/ns:MsgId', ns).text
    except AttributeError:
        pass
    
    try:
        dict['OriginalCreDtTm'] = datetime.fromisoformat(root.find('./ns:MndtAccptncRpt/ns:UndrlygAccptncDtls/ns:OrgnlMsgInf/ns:CreDtTm', ns).text)
    except AttributeError:
        pass
    
    try:
        dict['Accptd'] = root.find('./ns:MndtAccptncRpt/ns:UndrlygAccptncDtls/ns:AccptncRslt/ns:Accptd', ns).text
    except AttributeError:
        pass
    
    try:
        dict['UMRN'] = root.find('./ns:MndtAccptncRpt/ns:UndrlygAccptncDtls/ns:OrgnlMndt/ns:OrgnlMndt/ns:MndtId', ns).text
    except AttributeError:
        pass
    
    try:
        dict['Error'] = root.find('./ns:MndtAccptncRpt/ns:UndrlygAccptncDtls/ns:AccptncRslt/ns:RjctRsn/ns:Prtry', ns).text
    except AttributeError:
        pass
    
    try:
        dict['MndtReqId'] =  root.find('./ns:MndtAccptncRpt/ns:UndrlygAccptncDtls/ns:OrgnlMndt/ns:OrgnlMndt/ns:MndtReqId', ns).text
    except AttributeError:
        pass
    
    try:
        dict['Dt'] =  date.fromisoformat(root.find('./ns:MndtAccptncRpt/ns:UndrlygAccptncDtls/ns:OrgnlMndt/ns:OrgnlMndt/ns:Ocrncs/ns:Drtn/ns:FrDt', ns).text)
    except AttributeError:
        pass
    
    try:
        dict['FrstColltnDt'] =  date.fromisoformat(root.find('./ns:MndtAccptncRpt/ns:UndrlygAccptncDtls/ns:OrgnlMndt/ns:OrgnlMndt/ns:Ocrncs/ns:FrstColltnDt', ns).text)
    except AttributeError:
        pass
    
    try:
        dict['FnlColltnDt'] =  date.fromisoformat(root.find('./ns:MndtAccptncRpt/ns:UndrlygAccptncDtls/ns:OrgnlMndt/ns:OrgnlMndt/ns:Ocrncs/ns:FnlColltnDt', ns).text)
    except AttributeError:
        pass
    
    try:
        dict['Amt'] =  Decimal(root.find('./ns:MndtAccptncRpt/ns:UndrlygAccptncDtls/ns:OrgnlMndt/ns:OrgnlMndt/ns:ColltnAmt', ns).text)
    except AttributeError:
        pass
    
    try:
        dict['DbtrName'] =  root.find('./ns:MndtAccptncRpt/ns:UndrlygAccptncDtls/ns:OrgnlMndt/ns:OrgnlMndt/ns:Dbtr/ns:Nm', ns).text
    except AttributeError:
        pass
    
    try:
        dict['DbtrAcct'] =  root.find('./ns:MndtAccptncRpt/ns:UndrlygAccptncDtls/ns:OrgnlMndt/ns:OrgnlMndt/ns:DbtrAcct/ns:Id/ns:Othr/ns:Id', ns).text
    except AttributeError:
        pass
    
    try:
        dict['DbtrAcctType'] =  root.find('./ns:MndtAccptncRpt/ns:UndrlygAccptncDtls/ns:OrgnlMndt/ns:OrgnlMndt/ns:DbtrAcct/ns:Tp/ns:Prtry', ns).text
    except AttributeError:
        pass
    
    try:
        dict['DbtrAcctIFSC'] =  root.find('./ns:MndtAccptncRpt/ns:UndrlygAccptncDtls/ns:OrgnlMndt/ns:OrgnlMndt/ns:DbtrAgt/ns:FinInstnId/ns:ClrSysMmbId/ns:MmbId', ns).text
    except AttributeError:
        pass
    
    return dict


#def zip2csv(data):
fieldnames = [
    'AcqMsgId',
    'AcqCreDtTm',
    'OriginalMsgId',
    'OriginalCreDtTm',
    'MndtReqId',
    'Dt',
    'FrstColltnDt',
    'FnlColltnDt',
    'Amt',
    'DbtrName',
    'DbtrAcct',
    'DbtrAcctType',
    'DbtrAcctIFSC',
    'Accptd',
    'UMRN',
    'Error',
]

def zip2dict(zip_file):
    with zipfile.ZipFile(zip_file) as zip:
        ack_files = []
        for file in zip.infolist():
            dict = xml2dict(zip.open(file))
            dict['filename'] = file.filename
            ack_files.append(dict)
        print('zip2dict returning a list of ' + str(len(ack_files)) + ' dicts.')
        return ack_files
