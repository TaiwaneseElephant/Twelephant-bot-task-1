# -*- coding: utf-8 -*-
import pywikibot
from pywikibot import textlib
import mwparserfromhell as mwparser
import re
import time
import calendar
from datetime import datetime
import json
import math
import copy


__copyright__ = "Copyright (c) Taiwanese Elephant"

TIME_STAMP_PATTERN = re.compile(r"\d\d\d\d年\d{1,2}月\d{1,2}日 \([一二三四五六日]\) \d\d:\d\d \(UTC\)")

def find_signature_timestamp(text:str) -> list:
    return [i.group() for i in TIME_STAMP_PATTERN.finditer(text)]

def save(site, page:str, text:str, summary:str = "", add = False, minor = True, max_retry_times = 3):
    e = None
    oringinal_text = ""
    if add and page.exists():
        oringinal_text = page.get(force = True, get_redirect = True)
    for _ in range(max_retry_times):
        try:
            if add and page.exists():
                page.text = oringinal_text + text
            else:
                page.text = text
            page.save(summary, minor = minor)
            return True
        except pywikibot.exceptions.EditConflictError as e:
            print(f"Warning! There is an edit conflict on page '{page.title()}'!")
            oringinal_text = page.get(force = True, get_redirect = True)
        except pywikibot.exceptions.LockedPageError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed because the page is protected!")
            break
        except pywikibot.exceptions.AbuseFilterDisallowedError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed by the AbuseFilter!")
            break
        except pywikibot.exceptions.SpamblacklistError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed by the SpamFilter because the edit add blacklisted URL!")
            break
        except pywikibot.exceptions.TitleblacklistError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed because the title is blacklisted!")
            break
    print(f"The attempt to edit the page '{page.title()}' was stopped because of the error below:\n{e}\nThe edit is '{text[:100]}', and the summary is '{summary}'.")
    return False

def archive(archive_page_name:str, site, archive_list:list, sections, talk_page_name:str, header:str, counter_used:bool = False, counter:int = 0, \
            maxarchivesize:list = ["Bytes", 1000000000], depth:int = 0):
    if depth > 10:
        return counter, archive_list
    archive_page = pywikibot.Page(site, archive_page_name.replace("%(counter)d", str(counter)))
    if counter_used:
        counter_num = counter
        if maxarchivesize[0] == "Threads":
            max_sections_num = maxarchivesize[1] - len(textlib.extract_sections(archive_page.text, site).sections)
            if max_sections_num <= 0:
                counter_num += 1
            list_to_archive = archive_list
            last_list = []
            while True:
                archive_page = pywikibot.Page(site, archive_page_name.replace("%(counter)d", str(counter_num)))
                if max_sections_num < len(archive_list):
                    text = "".join(f"\n{sections.sections[i].title}{sections.sections[i].content}" for i in list_to_archive[:max_sections_num])
                    if  not archive_page.exists():
                        text = f"{header}\n{text}"
                    saved = save(site, archive_page, text, f"Archived {min(max_sections_num, len(list_to_archive))} threads from [[{talk_page_name}]] by Twelephant-bot", \
                                 add = archive_page.exists())
                    new_counter, last_list = archive(archive_page_name, site, archive_list[max_sections_num:], sections, talk_page_name, header, \
                                                     True, counter_num + 1, maxarchivesize, depth + 1)
                    if not saved:
                        last_list += archive_list[:max_sections_num]
                    list_to_archive = archive_list[max_sections_num:]
                    counter_num += 1
                else:
                    text = "".join(f"\n{sections.sections[i].title}{sections.sections[i].content}" for i in list_to_archive)
                    if  not archive_page.exists():
                        text = f"{header}\n{text}"
                    saved = save(site, archive_page, text, f"Archived {len(archive_list)} threads from [[{talk_page_name}]] by Twelephant-bot", add = archive_page.exists())
                    if saved:
                        return counter_num, last_list
                    else:
                        return counter_num, last_list + list_to_archive
        elif maxarchivesize[0] == "Bytes":
            if  archive_page.exists():
                text = archive_page.text
            else:
                text = f"{header}\n"
            if len(text.encode("utf-8")) > maxarchivesize[1]:
                counter_num += 1
                archive_page = pywikibot.Page(site, archive_page_name.replace("%(counter)d", str(counter_num)))
            for i, j in enumerate(archive_list):
                text_ = f"{text}\n{sections.sections[j].title}{sections.sections[j].content}"
                if len(text_.encode("utf-8")) < maxarchivesize[1]:
                    text = text_
                else:
                    saved = save(site, archive_page, text, f"Archived {i} threads from [[{talk_page_name}]] by Twelephant-bot")
                    new_counter, last_list = archive(archive_page_name, site, archive_list[i:], sections, talk_page_name, header, \
                                                     True, counter_num + 1, maxarchivesize, depth + 1)
                    if saved:
                        return new_counter, last_list
                    else:
                        return new_counter, last_list + archive_list[:i]
            saved = save(site, archive_page, text, f"Archived {len(archive_list)} threads from [[{talk_page_name}]] by Twelephant-bot")
            if saved:
                return counter_num, []
            else:
                return counter_num, archive_list
        else:
            return counter, archive_list
    else:
        text = "".join(f"\n{sections.sections[i].title}{sections.sections[i].content}" for i in archive_list)
        if  not archive_page.exists():
            text = f"{header}\n{text}"
        saved = save(site, archive_page, text, f"Archived {len(archive_list)} threads from [[{talk_page_name}]] by Twelephant-bot", add = archive_page.exists())
        if saved:
            return 0, []
        else:
            return 0, archive_list

def del_archived(site, talk_page, del_list:set, unarchived:list = [], counter_used:bool = False, counter:int = 0, new_counter:int = 0, work_template_name:str = "", work_page_name:str = ""):
    talk_page.get(force = True, get_redirect = True)
    sections = textlib.extract_sections(talk_page.text, site)
    new_page_text = "".join(f"{sections.sections[i].title}{sections.sections[i].content}" for i in range(len(sections.sections)) if (i not in del_list) or (i in unarchived))
    text = sections.header + new_page_text
    if counter_used:
        text = mwparser.parse(text, skip_style_tags = True)
        template = text.filter_templates(matches = work_template_name)
        if template:
            template = template[0]
            old_template = str(template)
            template.add("counter", str(new_counter), preserve_spacing = True)
            text = str(text)
            work_page = pywikibot.Page(site, work_page_name)
            page_list = json.loads(work_page.text)
            page_list[talk_page.title()]["counter"] = new_counter
        else:
            work_page = pywikibot.Page(site, work_page_name)
            page_list = json.loads(work_page.text)
            if talk_page.title() in page_list:
                del page_list[talk_page.title()]
        json_text = json.dumps(page_list, ensure_ascii = False, indent = 4, sort_keys = True)
        save(site, work_page, json_text, "Updated by Twelephant-bot")
    save(site, talk_page, text, f"Archived {len(del_list) - len(unarchived)} threads by Twelephant-bot")

def archive_page(page_name:str, site, archive_page_name:str = "%(page)s/存檔%(counter)d", archive_time:list = ["old", 86400], counter:int = 1, minthreadsleft:int = 5, minthreadstoarchive:int = 2, \
                 archiveheader:str = "{{talkarchive}}", maxarchivesize:[str, int] = ["Bytes", 1000000000], custom_rules:list = [], work_page_name:str = "", work_template_name:str = "", **kwargs):
    talk_page = pywikibot.Page(site, page_name)
    timestripper = textlib.TimeStripper(site)
    sections = textlib.extract_sections(talk_page.text, site)
    threads_num = len(sections.sections)
    maxthreadstoarchive = max(threads_num - minthreadsleft, 0)
    del_list = set()
    time_type = archive_time[0]
    archive_standard = archive_time[1]
    date_used = ("%(year)d" in archive_page_name) or ("%(month)d" in archive_page_name) or ("%(quarter)d" in archive_page_name) 
    counter_used = ("%(counter)d" in archive_page_name) and not date_used
    archive_list = {None : []}

    for i in range(threads_num):
        if len(del_list) == maxthreadstoarchive:
            break
        content = sections.sections[i].content
        if "{{不存檔}}" in content:
            continue
        if (signature_timestamp := find_signature_timestamp(content)):
            title = sections.sections[i].title.strip().strip("==").strip()
            print(title)
            last_timestamp = 0
            last_time = None
            custom_rules_used  = False
            fail = False
            if custom_rules != []:
                for rule, custom_time_type, custom_standard in custom_rules:
                    if re.match(rule, title):
                        if custom_time_type == "old":
                            for j in signature_timestamp:
                                time_then = timestripper.timestripper(j).timetuple()
                                timestamp = calendar.timegm(time_then)
                                time_diff = time.time() - timestamp
                                if time_diff < custom_standard:
                                    fail = True
                                    break
                                if timestamp > last_timestamp:
                                    last_time = time_then
                        elif custom_time_type == "last":
                            if custom_standard[0] == "y":
                                for j in signature_timestamp:
                                    time_then = timestripper.timestripper(j).timetuple()
                                    if (time.gmtime().tm_year - time_then.tm_year) < custom_standard[1]:
                                        fail = True
                                        break
                                    if calendar.timegm(time_then) > last_timestamp:
                                        last_time = time_then
                            elif custom_standard[0] == "m":
                                for j in signature_timestamp:
                                    time_then = timestripper.timestripper(j).timetuple()
                                    if ((time.gmtime().tm_year - time_then.tm_year) * 12 + (time.gmtime().tm_mon - time_then.tm_mon)) < custom_standard[1]:
                                        fail = True
                                        break
                                    if calendar.timegm(time_then) > last_timestamp:
                                        last_time = time_then
                            elif custom_standard[0] == "w":
                               for j in signature_timestamp:
                                    time_then = timestripper.timestripper(j).timetuple()
                                    if (datetime.utcnow().isocalendar()[1] - datetime(*time_then[:6]).isocalendar()[1]) < custom_standard[1]:
                                        fail = True
                                        break
                                    if calendar.timegm(time_then) > last_timestamp:
                                        last_time = time_then
                            elif custom_standard[0] == "d":
                                for j in signature_timestamp:
                                    time_then = timestripper.timestripper(j).timetuple()
                                    if ((time.gmtime().tm_year - time_then.tm_year) * 365 + (time.gmtime().tm_yday - time_then.tm_yday)) < custom_standard[1]:
                                        fail = True
                                        break
                                    if calendar.timegm(time_then) > last_timestamp:
                                        last_time = time_then
                        custom_rules_used  = True
                        break
            if not custom_rules_used:
                fail = False
                if time_type == "old":
                    for j in signature_timestamp:
                        time_then = timestripper.timestripper(j).timetuple()
                        timestamp = calendar.timegm(time_then)
                        time_diff = time.time() - timestamp
                        if time_diff < archive_standard:
                            fail = True
                            break
                        if timestamp > last_timestamp:
                            last_time = time_then
                elif time_type == "last":
                    if archive_standard[0] == "y":
                        for j in signature_timestamp:
                            time_then = timestripper.timestripper(j).timetuple()
                            if (time.gmtime().tm_year - time_then.tm_year) < archive_standard[1]:
                                fail = True
                                break
                            if calendar.timegm(time_then) > last_timestamp:
                                last_time = time_then
                    elif archive_standard[0] == "m":
                        for j in signature_timestamp:
                            time_then = timestripper.timestripper(j).timetuple()
                            if ((time.gmtime().tm_year - time_then.tm_year) * 12 + (time.gmtime().tm_mon - time_then.tm_mon)) < archive_standard[1]:
                                fail = True
                                break
                            if calendar.timegm(time_then) > last_timestamp:
                                last_time = time_then
                    elif custom_standard[0] == "w":
                       for j in signature_timestamp:
                            time_then = timestripper.timestripper(j).timetuple()
                            if (datetime.utcnow().isocalendar()[1] - datetime(*time_then[:6]).isocalendar()[1]) < custom_standard[1]:
                                fail = True
                                break
                            if calendar.timegm(time_then) > last_timestamp:
                                last_time = time_then
                    elif archive_standard[0] == "d":
                        for j in signature_timestamp:
                            time_then = timestripper.timestripper(j).timetuple()
                            if ((time.gmtime().tm_year - time_then.tm_year) * 365 + (time.gmtime().tm_yday - time_then.tm_yday)) < archive_standard[1]:
                                fail = True
                                break
                            if calendar.timegm(time_then) > last_timestamp:
                                last_time = time_then
            if not fail:
                if date_used and last_time:
                    if (last_time.tm_year, last_time.tm_mon) in archive_list:
                        archive_list[(last_time.tm_year, last_time.tm_mon)].append(i)
                    else:
                        archive_list[(last_time.tm_year, last_time.tm_mon)] = [i]
                else:
                    archive_list[None].append(i)
                del_list.add(i)
        else:
            continue

    if del_list != set() and len(del_list) >= minthreadstoarchive:
        if counter_used:
            unarchived = []
            result = archive(archive_page_name = archive_page_name, site = site, archive_list = archive_list[None], sections = sections, talk_page_name = page_name, \
                            header = archiveheader, counter_used = True, counter = counter, maxarchivesize = maxarchivesize)
            unarchived.extend(result[1])
            new_counter = result[0]
            del_archived(site, talk_page, del_list, unarchived, True, counter, new_counter, work_template_name, work_page_name)

        elif date_used:
            for i in archive_list.keys():
                achive_name = archive_page_name.replace("%(year)d", str(i[0])).replace("%(month)d", str(i[1])).replace("%(quarter)d", str(math.ceil(i[1] / 3)))
                archive(archive_page_name = achive_name, site = site, archive_list = archive_list[i], sections = sections, talk_page_name = page_name, \
                        header = archiveheader, counter_used = False)
            del_archived(site, talk_page, del_list, archive_list[None])
        else:
            archive(archive_page_name = achive_page_name, site = site, archive_list = archive_list[None], sections = sections, talk_page_name = page_name, \
                    header = archiveheader, counter_used = False)
            del_archived(site, talk_page, del_list)

def get_page_list(site, work_page_name:str, work_template_name:str) -> dict:
    page_list = pywikibot.Page(site, work_template_name).getReferences(follow_redirects = False, only_template_inclusion = True, namespaces = 3, content = True)
    result = {}
    default = {"archive_page_name":"%(page)s/存檔%(counter)d", "archive_time" : ["old", 86400], "counter" : 1, "maxarchivesize" : ["Bytes", 1000000000], \
               "minthreadsleft" : 5, "minthreadstoarchive" : 2, "archiveheader" : "{{talkarchive}}", "custom_rules" : []}
    option_rules = {"afd" : r".*?页面存废讨论通知", "csd" : r".*?的快速删除通知", "ifd" : r".*?-\{zh-hans:文件;zh-hant:檔案;\}-存廢討論通知", \
                    "nolicense" : r"(?:.*?的著作權問題)|(?:.*?的檔案授權許可問題)|(?:.*?的檔案來源與著作權標籤問題)", \
                    "nosource" : r"(?:.*?的來源問題)|(?:.*?的檔案來源與著作權標籤問題)", "norationale" : r".*?缺乏合理使用依據通知", \
                    "orfud" : r"未被条目使用的非自由版权图片.*?", "replaceable" : r"可被替代的非自由檔案.*?快速刪除通知", "rfc" : r"\d\d\d\d年\d{1,2}月徵求意見討論邀請"}
    for i in page_list:
        if not i.botMayEdit():
            continue 
        text = mwparser.parse(i.text, skip_style_tags = True)
        if not (match := text.filter_templates(matches = work_template_name)):
            continue
        title = i.title()
        match = match[0]
        result[title] = copy.deepcopy(default)
        for parameter in match.params:
            key = parameter.name.strip()
            item = parameter.value.strip()
            if key == "archive":
                if item.startswith("/"):
                    result[title]["archive_page_name"] = f"{title}{item}"
                elif item.startswith(f"{title}/") or item.startswith(f"%(page)s/"):
                    result[title]["archive_page_name"] = item.replace("%(page)s", title)
                else:
                    result[title]["archive_page_name"] = f"{title}/{item}"
            elif key == "algo":
                item = item.replace(" ", "").lower()
                match1 = re.match(r"old\((\d+)([wdh])\)", item)
                match2 =  re.match(r"last\((\d+)([ymd])\)", item)
                if match1:
                    var = {"w":604800, "d":86400, "h":3600}
                    var1, var2 = match1.groups()
                    result[title]["archive_time"]  = ["old", int(var1) * var[var2]]
                elif match2:
                    var1, var2 = match2.groups()
                    result[title]["archive_time"]  = ["last", [var2, int(var1)]]
            elif key in ("counter", "minthreadsleft", "minthreadstoarchive"):
                item = item.replace(" ", "")
                if item.isdigit():
                    result[title][key] = int(item)
            elif key  == "maxarchivesize":
                item = item.replace(" ", "")
                if re.match(r"\d+[MKT]", item):
                    if (num := int(item[:-1])) == 0:
                        continue
                    var1 = {"M":"Bytes", "K":"Bytes", "T":"Threads"}
                    var2 = {"M":1000000, "K":1000, "T":1}
                    result[title]["maxarchivesize"] = [var1[item[-1]], (num * var2[item[-1]])]
            elif key == "archiveheader":
                result[title]["archiveheader"] = item
            elif key.startswith("custom"):
                var = re.match(r"(.*?);(old|last)\s*\(\s*(\d+)\s*([ymwdh])\s*\)$", item)
                if var:
                    var1, var2, var3, var4 = var.groups()
                    if var2 == "old" and var4 in ("w", "d", "h"):
                        var = {"w":604800, "d":86400, "h":3600}
                        result[title]["custom_rules"].append([var1, "old", int(var3) * var[var4]])
                    elif var2 == "last" and var4 in ("y", "m", "d"):
                        result[title]["custom_rules"].append([var1, "last", [var4, int(var3)]])
            elif key in option_rules:
                item = item.replace(" ", "").lower()
                match1 = re.match(r"old\((\d+)([wdh])\)", item)
                match2 =  re.match(r"last\((\d+)([ymd])\)", item)
                if match1:
                    var = {"w":604800, "d":86400, "h":3600}
                    var1, var2 = match1.groups()
                    result[title]["custom_rules"].append([option_rules[key], "old", int(var1) * var[var2]])
                elif match2:
                    var1, var2 = match2.groups()
                    result[title]["custom_rules"].append([option_rules[key], "last", [var2, int(var1)]])
        result[title]["archive_page_name"] = result[title]["archive_page_name"].replace("%(page)s", title)
        result[title]["archiveheader"] = result[title]["archiveheader"].replace("%(page)s", title)
    work_page = pywikibot.Page(site, work_page_name)
    old_page_list = json.loads(work_page.text)
    if old_page_list != result:
        print(old_page_list)
        print(result)
        welcome_newcomers(result, old_page_list, site)
        text = json.dumps(result, ensure_ascii = False, indent = 4)
        save(site, work_page, text, "Updated by Twelephant-bot")
    return result

def send_message(site, talk_page_name:str, message:str, summary:str):
    talk_page = pywikibot.Page(site, talk_page_name)
    save(site, talk_page, message, summary, add = True, minor = False)

def send_welcome_message(talk_page_name:str, site):
    send_message(site, talk_page_name, "{{subst:User:Twelephant-bot/welcome message}}", "Welcoming user for using Twelephant-bot user talk page archive service by Twelephant-bot.")

def welcome_newcomers(new_page_list:dict, old_page_list:dict, site):
    bots = []
    for i in new_page_list.keys():
        if i not in old_page_list.keys():
            send_welcome_message(i, site)

def check_switch(site, switch_page_name:str) -> bool:
    switch_page = pywikibot.Page(site, switch_page_name)
    return json.loads(switch_page.text)["Archive User talk page"]["Enable"]

def run():
    site = pywikibot.Site('wikipedia:zh')
    work_page_name = "User:Twelephant-bot/Work page.json"
    work_template_name = "User:Twelephant-bot/Archive"
    if check_switch(site, "User:Twelephant-bot/setting.json"):
        page_list = get_page_list(site, work_page_name, work_template_name)
        for page, pref in page_list.items():
            if check_switch(site, "User:Twelephant-bot/setting.json"):
                try:
                    archive_page(page, site = site, work_page_name = work_page_name, work_template_name = work_template_name, **pref)
                    print(page)
                except  Exception as e:
                    print(f"Skipped page '{page}', its prefercence is {pref}, and the error is {e}")
        print(f"Sleep for 600 seconds since{time.gmtime()}.")
        time.sleep(600)

if __name__ == "__main__":
    run()
