import sys
import subprocess
import re
import time
import logging
from xml.sax.saxutils import escape
import pickle

#setup logging
logger = logging.getLogger('rtm-for-alfred2')
hdlr = logging.FileHandler('rtm-for-alfred.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.WARNING)

#constants
LIST_ARG = "list"
TASK_ARG = "task"
ACTION_ARG = "action"
RE_PRI_HIGH = re.compile(';202')
RE_PRI_MED = re.compile(';32')
RE_PRI_LOW = re.compile(';75')
RE_TODAY = re.compile(';1m')
RE_OVERDUE = re.compile(';1;4m')
RE_CLEAR = re.compile('\033\[[\d;]+m')
RE_RECURRING = re.compile('\(R\)')
CACHE_FILE = "rtm.p"
CACHE_LIST_TTL = 120
CACHE_TASK_TTL = 120

#Alfred filter string templates
rtmBlockBegin = """<?xml version="1.0"?>
<items>"""
rtmItemBlock = """<item uid="{UID}" arg="{ARG}" valid="{VALID}" autocomplete="{AUTOCOMPLETE}">
    <title>{TITLE}</title>
    <subtitle>{SUBTITLE}</subtitle>
    <icon>{ICON}</icon>
  </item>"""
rtmEndBlock = """</items>"""

def check_output(arr):
  if "check_output" not in dir( subprocess ):
    return subprocess.Popen(arr, stdout=subprocess.PIPE).communicate()[0]
  else:
    return subprocess.check_output(arr)

#cache dict
try:
  cache = pickle.load( open( CACHE_FILE, "rb" ) )
except Exception, e:
  cache = dict()


#input
#logger.debug("Query String: "+str(sys.argv).translate(None, "'"))
args = dict()
query = ""
argList = sys.argv
argList.pop(0)
argList = (" ".join(argList)).split(" ")

for arg in argList:
  p = arg.strip().split(":")
  if(len(p) == 2 and query == ""):
    args[p[0]] = p[1]
  else:
    query += arg + " "
query = query.strip();
ts = time.time();
#logger.debug("args length: "+str(len(args)))
#logger.debug("args: "+str(args).translate(None, "'"))
#logger.debug("query: "+query)

#output
if len(args) == 0 and query.startswith("add"):
  taskname = re.sub('^add ','',query)
  print rtmBlockBegin
  print rtmItemBlock.replace("{TITLE}", "Add Task: "+taskname)\
    .replace("{SUBTITLE}","").replace("{ICON}","rtm_icon.png")\
    .replace("{UID}",str(ts)).replace("{ARG}","action:add "+taskname)\
    .replace("{AUTOCOMPLETE}", "")\
    .replace("{VALID}", "yes")
  print rtmEndBlock
elif len(args) == 0:
  if "list_cache_time" in cache:
    cacheTime = cache["list_cache_time"]
  else:
	cacheTime = ts
  if "list_cache" in cache:
    ret = cache["list_cache"]
  else:
    ret = None
  if ret == None or ((ts - cacheTime) > CACHE_LIST_TTL):
    ret = check_output(["milkmaid","list"])
    cache["list_cache"] = ret
    cache["list_cache_time"] = ts
  if ret <> "":
    aList =  ret.split('\n');
    print rtmBlockBegin
    print rtmItemBlock.replace("{TITLE}", "Add A Task...")\
        .replace("{SUBTITLE}","").replace("{ICON}","rtm_icon.png")\
        .replace("{UID}",str(ts)).replace("{ARG}","")\
        .replace("{AUTOCOMPLETE}", "add ")\
        .replace("{VALID}", "no")
    for item in aList:
      if item <> "":
        parts = item.split(": ");
        print rtmItemBlock.replace("{TITLE}", escape(item))\
        .replace("{SUBTITLE}","").replace("{ICON}","rtm_icon.png")\
        .replace("{UID}",str(ts)).replace("{ARG}","")\
        .replace("{AUTOCOMPLETE}", "list:"+parts[0])\
        .replace("{VALID}", "no")
        ts += 1
    print rtmEndBlock
elif len(args) == 1 and (LIST_ARG in args):
  if "task_cache_time" in cache:
    cacheTime = cache["task_cache_time"]
  else:
	cacheTime = ts
  tcache = dict()
  if "task_cache" in cache:
    tcache = cache["task_cache"]
    if args[LIST_ARG] in tcache:
      ret = tcache[args[LIST_ARG]]
    else:
      ret = None
  else:
    ret = None
  if ret == None or ((ts - cacheTime) > CACHE_TASK_TTL):
    ret = check_output(["milkmaid","task", "-l", args[LIST_ARG]])
    tcache[args[LIST_ARG]] = ret
    cache["task_cache"] = tcache
    cache["task_cache_time"] = ts
  aList =  ret.split('\n');
  print rtmBlockBegin
  print rtmItemBlock.replace("{TITLE}", "Back...")\
      .replace("{SUBTITLE}","").replace("{ICON}","rtm_icon.png")\
      .replace("{UID}",str(ts)).replace("{ARG}","")\
      .replace("{AUTOCOMPLETE}", "")\
      .replace("{VALID}", "no")
  ts += 1
  for item in aList:
    if item <> "":
      pri = 0
      today = False
      overdue = False
      recurring = False
      if RE_PRI_HIGH.search(item) <> None:
        pri = 1
      if RE_PRI_MED.search(item) <> None:
        pri = 2
      if RE_PRI_LOW.search(item) <> None:
        pri = 3
      if RE_TODAY.search(item) <> None:
        today = True
      if RE_OVERDUE.search(item) <> None:
        overdue = True
      if RE_RECURRING.search(item) <> None:
        recurring = True
      item = RE_CLEAR.sub("",item)
      parts = item.split(": ");
      subtitle = ""
      icon = "rtm_icon.png"
      if pri > 0:
        icon = "rtm_icon_"+str(pri)+".png"
      if(today):
        subtitle = "Due Today"
      if(overdue):
        subtitle = "Overdue!"
      if(recurring):
        subtitle = "(Recurring) " + subtitle
      print rtmItemBlock.replace("{TITLE}", escape(item))\
      .replace("{SUBTITLE}",subtitle).replace("{ICON}",icon)\
      .replace("{UID}",str(ts)).replace("{ARG}","")\
      .replace("{AUTOCOMPLETE}", "list:"+args[LIST_ARG]+" "+"task:"+parts[0]+" "+escape(parts[1]))\
      .replace("{VALID}", "no")
      ts += 1
  print rtmEndBlock
elif len(args) == 2 and (LIST_ARG in args) and (TASK_ARG in args):
  print rtmBlockBegin
  print rtmItemBlock.replace("{TITLE}", "Back...")\
        .replace("{SUBTITLE}", "").replace("{ICON}","rtm_icon.png")\
        .replace("{UID}",str(ts)).replace("{ARG}","list:"+args[LIST_ARG])\
        .replace("{AUTOCOMPLETE}", "list:"+args[LIST_ARG])\
        .replace("{VALID}", "no")
  ts += 1
  print rtmItemBlock.replace("{TITLE}", "Complete This Task")\
        .replace("{SUBTITLE}", query).replace("{ICON}","rtm_icon.png")\
        .replace("{UID}",str(ts)).replace("{ARG}","list:"+args[LIST_ARG]+" "+"task:"+args[TASK_ARG]+" action:complete "+query)\
        .replace("{AUTOCOMPLETE}", "")\
        .replace("{VALID}", "yes")
  ts += 1
  print rtmItemBlock.replace("{TITLE}", "Postpone This Task")\
        .replace("{SUBTITLE}", query).replace("{ICON}","rtm_icon.png")\
        .replace("{UID}",str(ts)).replace("{ARG}","list:"+args[LIST_ARG]+" "+"task:"+args[TASK_ARG]+" action:postpone "+query)\
        .replace("{AUTOCOMPLETE}", "")\
        .replace("{VALID}", "yes")
  ts += 1
  print rtmItemBlock.replace("{TITLE}", "Delete This Task")\
        .replace("{SUBTITLE}", query).replace("{ICON}","rtm_icon.png")\
        .replace("{UID}",str(ts)).replace("{ARG}","list:"+args[LIST_ARG]+" "+"task:"+args[TASK_ARG]+" action:delete "+query)\
        .replace("{AUTOCOMPLETE}", "")\
        .replace("{VALID}", "yes")
  print rtmEndBlock
elif len(args) == 3 and (LIST_ARG in args) and (TASK_ARG in args) and (ACTION_ARG in args):
  ret = check_output(["milkmaid","task", args[ACTION_ARG], args[TASK_ARG], "-l", args[LIST_ARG]])
  if args[ACTION_ARG] == "complete":
    print "Completed Task: "+query
  if args[ACTION_ARG] == "postpone":
    print "Postponed Task: "+query
  if args[ACTION_ARG] == "delete":
    print "Deleted Task: "+query
  try:
    del cache["task_cache"]
    del cache["task_cache_time"]
  except Exception, e:
    ignore = ""
elif len(args) == 1 and (args[ACTION_ARG] == "add"):
  ret = check_output(["milkmaid","task", args[ACTION_ARG], query])
  print "Added Task: "+query
  try:
    del cache["task_cache"]
    del cache["task_cache_time"]
  except Exception, e:
    ignore = ""
else:
  print rtmBlockBegin
  print rtmItemBlock.replace("{TITLE}", "I don't know what you want to do?")\
  .replace("{SUBTITLE}","").replace("{ICON}","rtm_icon.png")\
  .replace("{UID}",str(ts)).replace("{ARG}","")\
  .replace("{AUTOCOMPLETE}", "")\
  .replace("{VALID}", "no")
  print rtmEndBlock

pickle.dump( cache, open( CACHE_FILE, "wb" ) )
