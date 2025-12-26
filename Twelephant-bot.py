# -*- coding: utf-8 -*-
import pywikibot
from pywikibot import textlib
import re
import time
import json
import math

HIDEN_TEXT_PATTERN = re.compile(r"<!--.*?-->|\s", flags = re.DOTALL)
TIME_STAMP_PATTERN = re.compile(r"\d\d\d\d年\d\d?月\d\d?日 \([一二三四五六日]\) \d\d:\d\d \(UTC\)")
DENYBOTS_PATTERN = re.compile(r"{{nobots|(?:bots\|(?:deny=(?:(?:.*?,)?all(?:,.*?)?|(?:.*?,)?Twelephant-bot(?:,.*?)?)|allow=(?:.*?,)?none(?:,.*?)?|optout=(?:.*?,)?all(?:,.*?)?))}}")

def find_signature_timestamp(text:str) -> list:
    return [i.group() for i in TIME_STAMP_PATTERN.finditer(text)]

def del_hiden_text(text:str) -> str:
    return HIDEN_TEXT_PATTERN.sub("", text)

def denybots(text:str) -> bool:
    return DENYBOTS_PATTERN.search(text)

def archive(archive_page_name:str, archive_list:set, sections, header:str, talk_page_name:str):
    text = "".join(f"\n{sections.sections[i].title}{sections.sections[i].content}" for i in archive_list)
    archive_page = pywikibot.Page(site, archive_page_name)
    if archive_page.exists():
        archive_page.text += text
    else:
        archive_page.text = f"{header}\n{text}"
    archive_page.save(f"Archived {len(num)} threads from [[{talk_page_name}]] by Twelephant-bot")
            
def del_archived(talk_page, del_list:set, sections):
    new_page_text = "".join(f"{sections.sections[i].title}{sections.sections[i].content}" for i in range(len(sections.sections)) if i not in del_list)
    talk_page.text = sections.header + new_page_text
    talk_page.save(f"Archived {len(del_list)} threads by Twelephant-bot")

def update_counter(page, work_page, new_counter:int):
    text = re.search(r"\{\{User:Twelephant-bot/Archive.*?\|\s*counter\s*=\s*\d*\s*[\|\}]", page.text, flags = re.DOTALL).group()
    counter_text = re.search(r"\|\s*counter\s*=\s*\d*\s*[\|\}]", text).group()
    new_counter_text = re.sub(r"\d*", str(new_counter), counter_text)
    next_text = text.replace(counter_text, new_counter_text, 1)
    page.text.replace(text, next_text, 1)
    page_list = json.loads(work_page.text)
    page_list[page.title()]["counter"] = new_counter
    work_page.text = json.dumps(page_list)
    work_page.save("Updated by Twelephant-bot")

def archive_page(page_name:str, archive_page_name:str = "%(page)s/存檔%(counter)d", archive_time:int = 604800, counter:int = 1, minthreadsleft:int = 1, minthreadstoarchive:int = 1, archiveheader:str = "{{Talkarchive}}", **kwargs):
    talk_page = pywikibot.Page(site, page_name)
    timestripper = textlib.TimeStripper(site)
    sections = textlib.extract_sections(talk_page.text, site)    
    threads_num = len(sections.sections)
    maxthreadstoarchive = threads_num - minthreadsleft
    archive_list = {}
    del_list = set()
    for i in range(threads_num):
        if len(del_list) == maxthreadstoarchive:
            break
        if sections.sections[i].content.startswith("{{Nosave}}"):
            continue
        if (signature_timestamp := find_signature_timestamp(sections.sections[i].content)):
            fail = False
            for j in signature_timestamp:
                time_then = timestripper.timestripper(j).timetuple()
                time_diff = time.mktime(time.gmtime()) - time.mktime(time_then)
                if time_diff < archive_time:
                    fail = True
                    break
            if fail:
                break
            if (time_then.tm_year, time_then.tm_mon) in archive_list:
                archive_list[(time_then.tm_year, time_then.tm_mon)].add(i) 
            else:
                archive_list[(time_then.tm_year, time_then.tm_mon)] = {i}
            del_list.add(i)
        else:
            break
    if del_list != set() and len(del_list) >= minthreadstoarchive:
        for i in archive_list.keys():
            achive_page_name_ = archive_page_name.replace("%(counter)d", str(counter)).replace("%(year)d", str(i[0])).replace("%(month)d", str(i[1])).replace("%(quarter)d", str(math.ceil(i[1] / 3)))
            archive(archive_page_name = achive_page_name_, archive_list = archive_list[i], sections = sections, header = archiveheader, talk_page_name = page_name)
        del_archived(talk_page, del_list, sections)
            
def update_work_page(work_page_name:str, work_template_name:str):
    page_list = pywikibot.Page(site, work_template_name).getReferences(follow_redirects = False, with_template_inclusion = True, only_template_inclusion = True, filter_redirects = False, namespaces = 3, total = None, content = False)
    result = {}
    default = {"archive_page_name":"%(page)s/存檔%(counter)d", "archive_time":604800, "counter":1, "maxarchivesize":(1000000000, "Bytes"), "minthreadsleft":1, "minthreadstoarchive":1, "archiveheader":"{{Talkarchive}}"}
    for i in page_list:
        if denybots(text):
            continue
        text = del_hiden_text(i.text)
        if not not (match := re.search(r"\{\{User:Twelephant-bot/Archive.*?\}\}", text)):
            continue
        title = i.title()
        result[title] = {}
        template_parameter = match.group()
        for j in template_parameter[2:-2].split("|"):
            if "=" in j:
                key, item = j.split("=", 1)
                if key in result[title]:
                    continue
                if key == "archive":
                    if item.startswith("/"):
                        result[title]["archive_page_name"] = f"{title}{item}"
                    elif item.startswith(f"{title}/") or item.startswith(f"%(page)s/"):
                        result[title]["archive_page_name"] = item
                    else:
                        result[title]["archive_page_name"] = f"{title}/{item}"
                elif key == "algo":
                    if re.match(r"old\(\d*[wdh]\)", item):
                        var = {"w":604800, "d":86400, "h":3600}
                        result[title]["archive_time"]  = int(item[4:-2]) * var[item[-2]]
                elif key in ("counter", "minthreadsleft", "minthreadstoarchive"):
                    if item.isdigit():
                        result[title][key] = int(item)
                elif key  == "maxarchivesize":
                    if re.match(r"\d*[MKT]", item):
                        var1 = {"M":"Bytes", "K":"Bytes", "T":"Threads"}
                        var2 = {"M":1000000, "K":1000, "T":1}
                        result[title]["maxarchivesize"] = (var1[item[-1]], (int(item[:-1]) * var2[item[-1]]))
                elif key == "archiveheader":
                    result[title]["archiveheader"] = item
        for j in default:  
            if j not in result[title]:
                result[title][j] = default[j]
        result[title]["archive_page_name"] = result[title]["archive_page_name"].replace("%(page)s", title) 
        result[title]["archiveheader"] = result[title]["archive_page_name"].replace("%(page)s", title)
        if "%(counter)d" not in result[title]["archive_page_name"]:
            del result[title]["counter"], result[title]["maxarchivesize"]
    work_page = pywikibot.Page(site, work_page_name)
    old_page_list = json.loads(work_page.text)
    if old_page_list != result:
        welcome_newcomers(result, old_page_list)
        work_page.text = json.dumps(result)
        work_page.save("Updated by Twelephant-bot")
    return result

def get_pages_to_archive(work_page_name:str) -> dict:
    work_page = pywikibot.Page(site, work_page_name)
    return json.loads(pywikibot.Page(site, work_page).text)

def send_massage(talk_page_name:str, massage:str, summary:str):
    talk_page = pywikibot.Page(site, talk_page_name)
    talk_page.text += massage
    talk_page.save(summary)

def send_welcome_massage(talk_page_name:str):
    send_massage(talk_page_name, "{{subst:User:Twelephant-bot/welcome message}}", "Welcoming user for using Twelephant-bot user talk page archive service by Twelephant-bot.")

def welcome_newcomers(new_page_list:dict, old_page_list:dict):
    bots = []
    for i in new_page_list.keys():
        if i not in old_page_list.keys():
            send_welcome_massage(i)

def check_switch(switch_page_name:str) -> bool:
    switch_page = pywikibot.Page(site, switch_page_name)
    return json.loads(switch_page.text)["Archive User talk page"]["Enable"]

if __name__ == "__main__":       
    site = pywikibot.Site('wikipedia:zh')
    times_limit = float("inf")
    times_now = 0
    work_page_name = "User:Twelephant-bot/Work page.json"
    update_work_page(work_page_name, "User:Twelephant-bot/Archive")
    while times_now < times_limit and check_switch("User:Twelephant-bot/setting.json"):
        page_list = get_pages_to_archive(work_page_name)
        for page, pref in page_list.items():
            archive_page(page, **pref)
        times_now += 1
