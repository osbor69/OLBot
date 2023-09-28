import os
import os.path
import telebot # install - pip install pytelegrambotapi
import time
import sys
import threading
from threading import Thread
##Запрос на консоль        
def yes_no_dialog(question, default_answer="yes"):
    answers = {"yes":1, "y":1, "ye":1, "no":0, "n":0}
    if default_answer == None: tip = " [y/n] "
    elif default_answer == "yes": tip = " [Y/n] "
    elif default_answer == "no": tip = " [y/N] "
    else: raise ValueError(f'Неверное значение: {default_answer = }')
    while True:
        print(question + tip + ": ", end="")
        user_answer = input().lower()
        if default_answer is not None and user_answer == '': return answers[default_answer]
        elif user_answer in answers: return answers[user_answer]
        else: print("Пожалуйста, введите yes/y или no/n\n")
## считывает файл параметров
def InitPrmFile(FileName):
    return({"name":FileName, "date":-1, "prm":{}})
def GetPrmFile(pf, lDate=True):
    if lDate:
        if os.path.exists(pf["name"]): d=os.path.getmtime(pf["name"])
        else: d=0
        lRead = d!=pf["date"]
        if lRead: pf["date"]=d
    else: lRead=True
    if lRead:
        pf["prm"]={}
        if os.path.exists(pf["name"]): 
            with open(pf["name"]) as fp: a=fp.readlines()
            for i in range(len(a)):
                s=a[i]
                p=s.find('=')
                pf["prm"][s[:p]]=s[p+1:-1]
def SetPrmFile(pf):
    f=open(pf["name"],"w")
    for p in pf["prm"]: f.write(p+'='+pf["prm"][p]+'\n')
    f.close()
def FileAddStr(FileName,sAdd):
    if os.path.exists(FileName):
        with open(FileName) as fp: s=fp.read()
    else: s=''
    with open(FileName,"w") as fp: fp.write(s+sAdd+'\n')
pfCDRN=InitPrmFile('OLBOT.PRM')
CdrN={}
ID_N={}
def GetPrm(lCdr=True):
    global pfCDRN,CdrN,ID_N
    GetPrmFile(pfCDRN,lCdr)
    if lCdr:
        CdrN={}
        ID_N={}
        for sn in pfCDRN["prm"]:
            s=pfCDRN["prm"][sn]
            pid=s.find(',')
            poff=s.find(',',pid+1)
            nid=s[pid+1:poff]
            if nid=='': nid=0
            else: nid=int(nid)
            CdrN[sn]={'fio': s[:pid], 'id': nid, 'off': s[poff+1:]=='T'}
            if nid!=0: ID_N[nid]=sn
##Изменяет CDR.TEL
def SetPrm():
    SetPrmFile(pfCDRN)
    GetPrm()
PathLog='LOG'
def Out(s):
    t=time.localtime()
    if isinstance(s,Exception): se=str(s)
    else: se=s
    with open(os.path.join(PathLog,time.strftime("%Y_%m_%d",t)),"a") as fp: fp.write(time.strftime("[%H:%M:%S]",t)+' '+se+'\n')
    print(time.strftime("[%d.%m.%Y %H:%M:%S]",t),s)
## считывает OLBOT.PRM
if not os.path.exists(PathLog): os.system('mkdir "'+PathLog+'"')
Out("Поддержка сообщений «Учёт клиентов <-> Telegram» включена")
GetPrm(False)
Path=pfCDRN["prm"]['PATH']
PathIn=os.path.join(Path,'входящие')
PathOut=os.path.join(Path,'исходящие')
FileRead=os.path.join(Path,'прочитанные')
FileReadOL=os.path.join(Path,'прочитанныеУК')
##При входе создать папку "входящие"
n=0
while not os.path.exists(PathIn):
    if n==0: n=1
    else: 
        if n==1:
            Out('Нет доступа к папке: '+PathIn+'. Повторяю проверку доступа...')
            n=2
        time.sleep(10)
    os.system('mkdir "'+PathIn+'"')
if n>0: Out('Доступ к папке '+PathIn+' успешно восстановлен.')
bot = telebot.TeleBot(pfCDRN["prm"]['GLOBID'])
pfCDRN=InitPrmFile(os.path.join(Path,'CDR.TEL'))
pfSent=InitPrmFile(os.path.join(Path,'отправленные'))
pfReadOL=InitPrmFile(FileReadOL)
##1) При входе и в цикле через 10 сек.
def PrOut():
    while True:
        ## получает список файлов папки "исходящие\*.*"
        if os.path.exists(PathOut):
            af=os.listdir(PathOut)
            ## для каждого файла, время которого не больше текущего
            for f in af:
                pf=os.path.join(PathOut,f)
                if os.path.getmtime(pf)<=time.time():
                    ## посылает в бот сообщение по ID получателя с содержимым файла и кнопкой «Прочитано»
                    p=f.find('_')
                    p1=f.find('_',p+1)
                    ## если нет информации о Msg.Recno
                    if p1==-1:
                        with open(pf) as fp: bot.send_message(f[:p], fp.read())
                    else:
                        markup = telebot.types.InlineKeyboardMarkup()
                        markup.add(telebot.types.InlineKeyboardButton(text='Прочитано', callback_data=3))
                        with open(pf) as fp: msg=bot.send_message(f[:p], fp.read(), reply_markup=markup)
                        ##при отправке исходящих в файле "отправленные" добавлять строку <ID сообщения>=<Msg.Recno>
                        GetPrmFile(pfSent)
                        pfSent["prm"][str(msg.id)]=f[p+1:p1]
                        SetPrmFile(pfSent)
                    ## потом файл удаляет
                    os.remove(pf)
        ##для каждой строки "прочитанныеУК"
        GetPrm()
        GetPrmFile(pfSent)
        GetPrmFile(pfReadOL)
        for p in pfReadOL["prm"]: 
            for key,value in pfSent["prm"].items():
                ##найти ID сообщения в "отправленные"
                if value==p:
                    ##убрать в Telegram кнопку "Прочитано" для найденного ID
                    n=CdrN.get(pfReadOL["prm"][p])
                    if n!=None:
                        try: bot.edit_message_reply_markup(n["id"], key)
                        except Exception as e: Out(e)
                    ##убрать найденную строку в "отправленные"
                    del pfSent["prm"][key]
                    SetPrmFile(pfSent)
                    break
        ##удалить "прочитанныеУК"
        if os.path.exists(FileReadOL): os.remove(FileReadOL)
        time.sleep(10)
##2) При получении сообщения от бота
def PrIn():
    @bot.message_handler(content_types=["text"])
    def GetText(message):
        GetPrm()
        idfrom=message.from_user.id
        nfrom=ID_N.get(idfrom)
        s=message.text
        lStart = s=='/start'
        ##если в CDR.TEL не описан ID отправителя
        if nfrom==None:
            ##если сообщение число
            if s.isdigit():
                n=CdrN.get(s)
                ##если этого номера нет в CDR.TEL
                if n==None: bot.send_message(idfrom,'Пользователь с № '+s+' отсутствует в «Учёте клиентов»')
                else:
                    if yes_no_dialog('Зарегистрировать пользователя '+message.from_user.first_name+' в «Учёте клиентов» с № '+s+'  ?')==1:
                        ##изменение CDR.TEL, считывает CDR.TEL
                        pfCDRN["prm"][s]=n['fio']+','+str(idfrom)+','+['F','T'][n['off']]
                        SetPrm()
                        ##посылает сообщение в бот по ID отправителя
                        bot.send_message(idfrom,'Вы успешное зарегистрированы в «Учёте клиентов»\nДля отправки сообщения другому пользователю:\n<№ получателя>.<текст>\nДля отключения/включения приёма сообщений от других пользователей:\n<текст>')
                    ##посылает сообщение в бот по ID отправителя
                    else: bot.send_message(idfrom,'В регистрации отказано')
            ##посылает сообщение в бот по ID отправителя
            elif lStart: bot.send_message(idfrom,'Для регистрации в «Учёте клиентов» необходимо отправить сообщение с № пользователя')
            else: bot.send_message(idfrom,'Вы не зарегистрированы в «Учёте клиентов»\nДля регистрации необходимо отправить сообщение с № пользователя')
        elif not lStart:
            p=s.find('.')
            nto=s[:p]
            ##если в тексте есть "." и до неё число(№ получателя) и № получателя есть в списке CDR.TEL
            if p>=0 and nto.isdigit() and CdrN.get(nto)!=None:
                ##создаёт в папке "входящие" файл № отправителя_№ получателя_YYYYMMDDHHNNSSZZZ с содержимым после "."
                s=s[p+1:]
                with open(os.path.join(PathIn,nfrom+'_'+nto+'_'+time.strftime('%Y%m%d%H%M%S',time.localtime(message.date))),"w") as fp: fp.write(s)
            else:
                ##посылает запрос в бот по ID отправителя
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton(text='Да', callback_data=1))
                markup.add(telebot.types.InlineKeyboardButton(text='Нет', callback_data=2))
                bot.send_message(idfrom, text=['Отключить','Включить'][CdrN.get(nfrom)['off']]+' приём сообщений от других пользователей ?', reply_markup=markup)
    @bot.callback_query_handler(func=lambda call: True)
    def query_handler(call):
        bot.answer_callback_query(callback_query_id=call.id)
        if call.data == '1':
            ##изменение CDR.TEL, считывает CDR.TEL
            nfrom=ID_N.get(call.from_user.id)
            n=CdrN.get(nfrom)
            pfCDRN["prm"][nfrom]=n['fio']+','+str(n['id'])+','+['F','T'][n['off']==False]
            SetPrm()
        elif call.data == '3':
            ##При нажатии в боте на кнопку «Прочитано» в файл "прочитанные" добавлять строку <Msg.Recno>
            GetPrmFile(pfSent)
            sid=str(call.message.id)
            FileAddStr(FileRead,pfSent["prm"][sid])
            ##убирать строку в файле "отправленные"  по ID сообщения
            del pfSent["prm"][sid]
            SetPrmFile(pfSent)
        ## Убрать кнопки
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    try: bot.polling()
    except Exception as e:
        Out(e)
        time.sleep(10)
        try: os.execv(sys.argv[0], sys.argv)
        except: quit()
ThreadOut = Thread(target=PrOut)
ThreadIn = Thread(target=PrIn)
ThreadOut.start()
ThreadIn.start()
ThreadOut.join()
ThreadIn.join()
