# -*- coding: utf-8 -*-
import pywikibot
from pywikibot import textlib
import mwparserfromhell as mwparser
import re
import time
import calendar
import json
import math
import copy


__copyright__ = "Copyright (c) Taiwanese Elephant"

TIME_STAMP_PATTERN = re.compile(r"\d\d\d\d年\d(?:\d)?月\d(?:\d)?日 \([一二三四五六日]\) \d\d:\d\d \(UTC\)")
DENYBOTS_PATTERN = re.compile(r"{{(?:bots\|(?:deny=(?:(?:.*?,)?all(?:,.*?)?|(?:.*?,)?twelephant-bot(?:,.*?)?)|allow=(?:.*?,)?none(?:,.*?)?|optout=(?:.*?,)?all(?:,.*?)?))}}")

def find_signature_timestamp(text:str) -> list:
    return [i.group() for i in TIME_STAMP_PATTERN.finditer(text)]

def denybots(wikitext) -> bool:
    return wikitext.filter_templates(matches = "Nobots") or DENYBOTS_PATTERN.search(str(wikitext.filter_templates(matches = "Bots")).lower())

def save(site, page:str, text:str, summary:str = "", add = False, minor = True, max_retry_times = 3):
    retry_times = 0
    e = None
    while retry_times < max_retry_times:
        try:
            if add and page.exists():
                page.text = page.get(force = True, get_redirect = True) + text
            else:
                page.text = text
            page.save(summary, minor = minor)
            return True
        except pywikibot.exceptions.EditConflictError as e:
            print(f"Warning! There is an edit conflict on page '{page.title()}'!")
            retry_times += 1
            if not add:
                page.get(force = True, get_redirect = True)
        except pywikibot.exceptions.LockedPageError as e:
            print(f"Warining! The edit attempt on page '{page.title()}' was disallowed because the page is protected!")
            break
        except pywikibot.exceptions.AbuseFilterDisallowedError as e:
            print(f"Warining! The edit attempt on page '{page.title()}' was disallowed by the AbuseFilter!")
            break
        except pywikibot.exceptions.SpamblacklistError as e:
            print(f"Warining! The edit attempt on page '{page.title()}' was disallowed by the SpamFilter because the edit add blacklisted URL!")
            break
        except pywikibot.exceptions.TitleblacklistError as e:
            print(f"Warining! The edit attempt on page '{page.title()}' was disallowed because the title is blacklisted!")
            break
    print(f"The attempt to edit the page '{page.title()}' was stopped because of the error below:\n{e}\nThe edit is '{text[:100]}', and the summary is '{summary}'.")
    return False

def archive(archive_page_name:str, site, archive_list:list, sections, talk_page_name:str, header:str, counter_used:bool = False, counter:int = 0, \
            maxarchivesize:list = ["Bytes", 1000000000], work_page_name:str = "", work_template_name:str = "", top:bool = True, depth:int = 0):
    if depth > 10:
        return counter, archive_list
    archive_page = pywikibot.Page(site, archive_page_name.replace("%(counter)d", str(counter)))
    if counter_used:
        if maxarchivesize[0] == "Threads":
            max_sections_num = maxarchivesize[1] - len(textlib.extract_sections(archive_page.text, site).sections)
            if max_sections_num <= 0:
                new_counter, last_list = archive(archive_page_name, site, archive_list, sections, talk_page_name, header, \
                                                 True, counter + 1, maxarchivesize, work_page_name, work_template_name, False, depth + 1)
                if top and counter != new_counter:
                    update_counter(talk_page_name, work_page_name, work_template_name, site, new_counter)
                return new_counter, last_list
            elif max_sections_num < len(archive_list):
                text = "".join(f"\n{sections.sections[i].title}{sections.sections[i].content}" for i in archive_list[:max_sections_num])
                if  not archive_page.exists():
                    text = f"{header}\n{text}"
                saved = save(site, archive_page, text, f"Archived {min(max_sections_num, len(archive_list))} threads from [[{talk_page_name}]] by Twelephant-bot", \
                             add = archive_page.exists())
                new_counter, last_list = archive(archive_page_name, site, archive_list[max_sections_num:], sections, talk_page_name, header, \
                                                 True, counter + 1, maxarchivesize, work_page_name, work_template_name, False, depth + 1)
                if top and counter != new_counter:
                    update_counter(talk_page_name, work_page_name, work_template_name, site, new_counter)
                if saved:
                    return new_counter, last_list
                else:
                    return new_counter, last_list + archive_list[:max_sections_num]
            else:
                text = "".join(f"\n{sections.sections[i].title}{sections.sections[i].content}" for i in archive_list)
                if  not archive_page.exists():
                    text = f"{header}\n{text}"
                saved = save(site, archive_page, text, f"Archived {len(archive_list)} threads from [[{talk_page_name}]] by Twelephant-bot", add = archive_page.exists())
                if saved:
                    return counter, []
                else:
                    return counter, archive_list
        elif maxarchivesize[0] == "Bytes":
            if  archive_page.exists():
                text = archive_page.text
            else:
                text = f"{header}\n"
            for i, j in enumerate(archive_list):
                text_ = f"{text}\n{sections.sections[j].title}{sections.sections[j].content}"
                if len(text_.encode("utf-8")) < maxarchivesize[1]:
                    text = text_
                else:
                    saved = save(site, archive_page, text, f"Archived {i} threads from [[{talk_page_name}]] by Twelephant-bot")
                    new_counter, last_list = archive(archive_page_name, site, archive_list[i:], sections, talk_page_name, header, \
                                                     True, counter + 1, maxarchivesize, work_page_name, work_template_name, False, depth + 1)
                    if top and counter != new_counter:
                        update_counter(talk_page_name, work_page_name, work_template_name, site, new_counter)
                    if saved:
                        return new_counter, last_list
                    else:
                        return new_counter, last_list + archive_list[:i]
            saved = save(site, archive_page, text, f"Archived {len(archive_list)} threads from [[{talk_page_name}]] by Twelephant-bot")
            if saved:
                return counter, []
            else:
                return counter, archive_list
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

def del_archived(site, talk_page, del_list:set, sections, unarchived:list):
    new_page_text = "".join(f"{sections.sections[i].title}{sections.sections[i].content}" for i in range(len(sections.sections)) if i not in del_list or i in unarchived)
    text = sections.header + new_page_text
    save(site, talk_page, text, f"Archived {len(del_list) - len(unarchived)} threads by Twelephant-bot")

def update_counter(page_name:str, work_page_name:str, work_template_name:str, site, new_counter:int):
    page = pywikibot.Page(site, page_name)
    text = mwparser.parse(page.text, skip_style_tags = True)
    template = text.filter_templates(matches = work_template_name)
    if template:
        template = template[0]
        old_template = str(template)
        template.add("counter", str(new_counter), preserve_spacing = True)
        text = str(text)
        save(site, page, text, "Updated by Twelephant-bot")
        work_page = pywikibot.Page(site, work_page_name)
        page_list = json.loads(work_page.text)
        page_list[page.title()]["counter"] = new_counter
    else:
        work_page = pywikibot.Page(site, work_page_name)
        page_list = json.loads(work_page.text)
        if page.title() in page_list:
            del page_list[page.title()]
    text = json.dumps(page_list, ensure_ascii = False, indent = 4, sort_keys = True)
    save(site, work_page, text, "Updated by Twelephant-bot")

def archive_page(page_name:str, site, archive_page_name:str = "%(page)s/存檔%(counter)d", archive_time:[str, int|list] = ["old", 86400], counter:int = 1, minthreadsleft:int = 5, minthreadstoarchive:int = 2, \
                 archiveheader:str = "{{talkarchive}}", maxarchivesize:list[str, int] = ["Bytes", 1000000000], custom_rules:list = [], work_page_name:str = "", work_template_name:str = "", **kwargs):
    talk_page = pywikibot.Page(site, page_name)
    timestripper = textlib.TimeStripper(site)
    sections = textlib.extract_sections(talk_page.text, site)
    threads_num = len(sections.sections)
    maxthreadstoarchive = max(threads_num - minthreadsleft, 0)
    del_list = set()
    time_type = archive_time[0]
    archive_standard = archive_time[1]
    date_used = ("%(year)d" in archive_page_name) or ("%(month)d" in archive_page_name) or ("%(quarter)d" in archive_page_name)
    if date_used:
        archive_list = {}
    else:
        archive_list = []

    for i in range(threads_num):
        if len(del_list) == maxthreadstoarchive:
            break
        content = sections.sections[i].content
        if mwparser.parse(content, skip_style_tags = True).filter_templates(matches = "Nosave"):
            continue
        if (signature_timestamp := find_signature_timestamp(content)):
            title = sections.sections[i].title
            custom_rules_used  = False
            fail = False
            if custom_rules != []:
                for rule, custom_time_type, custom_time in custom_rules:
                    if re.match(rule, title):
                        custom_rules_used  = True
                        for j in signature_timestamp:
                            time_then = timestripper.timestripper(j).timetuple()
                            if custom_time_type == "old":
                                time_diff = time.time() - calendar.timegm(time_then)
                                if time_diff < custom_time:
                                    fail = True
                                    break
                            elif custom_time_type == "last":
                                if archive_standard[0] == "y":
                                    if (time.gmtime().tm_year - time_then.tm_year) < archive_standard[1]:
                                        fail = True
                                        break
                                elif archive_standard[0] == "m":
                                    if (time.gmtime().tm_mon - time_then.tm_mon) < archive_standard[1]:
                                        fail = True
                                        break
                                elif archive_standard[0] == "d":
                                    if (time.gmtime().tm_yday - time_then.tm_yday) < archive_standard[1]:
                                        fail = True
                                        break
            if not custom_rules_used:
                fail = False
                for j in signature_timestamp:
                    time_then = timestripper.timestripper(j).timetuple()
                    if time_type == "old":
                        time_diff = time.time() - calendar.timegm(time_then)
                        if time_diff < archive_standard:
                            fail = True
                            break
                    elif time_type == "last":
                            if archive_standard[0] == "y":
                                if (time.gmtime().tm_year - time_then.tm_year) < archive_standard[1]:
                                    fail = True
                                    break
                            elif archive_standard[0] == "m":
                                if (time.gmtime().tm_mon - time_then.tm_mon) < archive_standard[1]:
                                    fail = True
                                    break
                            elif archive_standard[0] == "d":
                                if (time.gmtime().tm_yday - time_then.tm_yday) < archive_standard[1]:
                                    fail = True
                                    break
            if fail:
                continue
            if date_used:
                if (time_then.tm_year, time_then.tm_mon) in archive_list:
                    archive_list[(time_then.tm_year, time_then.tm_mon)].append(i)
                else:
                    archive_list[(time_then.tm_year, time_then.tm_mon)] = [i]
            else:
                archive_list.append(i)
            del_list.add(i)
        else:
            continue

    if del_list != set() and len(del_list) >= minthreadstoarchive:
        if ("%(counter)d" in archive_page_name):
            unarchived = []
            if date_used:
                for i in archive_list.keys():
                    achive_name = archive_page_name.replace("%(year)d", str(i[0])).replace("%(month)d", str(i[1])).replace("%(quarter)d", str(math.ceil(i[1] / 3)))
                    unarchived.extend(archive(archive_page_name = achive_name, site = site, archive_list = archive_list[i], sections = sections, talk_page_name = page_name, \
                            header = archiveheader, counter_used = True, counter = counter, maxarchivesize = maxarchivesize, work_page_name = work_page_name, \
                                      work_template_name = work_template_name)[1])
            else:
                unarchived.extend(archive(archive_page_name = archive_page_name, site = site, archive_list = archive_list, sections = sections, talk_page_name = page_name, \
                        header = archiveheader, counter_used = True, counter = counter, maxarchivesize = maxarchivesize, work_page_name = work_page_name, \
                                  work_template_name = work_template_name)[1])
            del_archived(site, talk_page, del_list, sections, unarchived)

        else:
            if date_used:
                for i in archive_list.keys():
                    achive_name = archive_page_name.replace("%(year)d", str(i[0])).replace("%(month)d", str(i[1])).replace("%(quarter)d", str(math.ceil(i[1] / 3)))
                    archive(archive_page_name = achive_name, site = site, archive_list = archive_list[i], sections = sections, talk_page_name = page_name, \
                            header = archiveheader, counter_used = False)
            else:
                archive(archive_page_name = achive_page_name, site = site, archive_list = archive_list, sections = sections, talk_page_name = page_name, \
                        header = archiveheader, counter_used = False)
            del_archived(site, talk_page, del_list, sections, [])

def update_work_page(site, work_page_name:str, work_template_name:str):
    def get_time(text):
        item = text.replace(" ", "").lower()
        match1 = re.match(r"old\((\d+)([wdh])\)", item)
        match2 =  re.match(r"last\((\d+)([ymd])\)", item)
        var = {"w":604800, "d":86400, "h":3600}
        if match1:
            var1, var2 = match1.groups()
            return ("old", int(var1) * var[var2])
        elif match2:
            var1, var2 = match2.groups()
            return ("last", [var2, int(var1)])
        else:
            return (None, None)
                
    page_list = pywikibot.Page(site, work_template_name).getReferences(follow_redirects = False, only_template_inclusion = True, namespaces = 3, content = False)
    result = {}
    default = {"archive_page_name":"%(page)s/存檔%(counter)d", "archive_time" : ("old", 86400), "counter" : 1, "maxarchivesize" : ["Bytes", 1000000000], "minthreadsleft" : 5, \
               "minthreadstoarchive" : 2, "archiveheader" : "{{talkarchive}}", "custom_rules" : []}
    for i in page_list:
        text = mwparser.parse(i.text, skip_style_tags = True)
        if denybots(text) or not (match := text.filter_templates(matches = work_template_name)):
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
                var1, var2 = get_time(item)
                if var1 != None:
                    result[title]["archive_time"]  = [var1, var2]
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
                if re.match(r".*?;\d+", item):
                    var = re.match(r"(.*?);(\d+)$", item)
                    if var:
                        var1, var2 = var.groups()
                        var3, var4 = get_time(var2)
                        if var3 != None:
                            result[title]["custom_rules"].append([var1, var3, var4])
        result[title]["archive_page_name"] = result[title]["archive_page_name"].replace("%(page)s", title)
        result[title]["archiveheader"] = result[title]["archiveheader"].replace("%(page)s", title)
        if "%(counter)d" not in result[title]["archive_page_name"]:
            del result[title]["counter"], result[title]["maxarchivesize"]
        if result[title]["custom_rules"] == []:
            del result[title]["custom_rules"]
    work_page = pywikibot.Page(site, work_page_name)
    old_page_list = json.loads(work_page.text)
    if old_page_list != result:
        welcome_newcomers(result, old_page_list, site)
        text = json.dumps(result, ensure_ascii = False, indent = 4, sort_keys = True)
        save(site, work_page, text, "Updated by Twelephant-bot")
    return result

def get_pages_to_archive(site, work_page_name:str) -> dict:
    work_page = pywikibot.Page(site, work_page_name)
    return json.loads(work_page.text)

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

if __name__ == "__main__":
    SITE = pywikibot.Site('wikipedia:zh')
    times_limit = float("inf")
    times_now = 0
    WORK_PAGE_NAME = "User:Twelephant-bot/Work page.json"
    WORK_TEMPLATE_NAME = "User:Twelephant-bot/Archive"
    while times_now < times_limit and check_switch(SITE, "User:Twelephant-bot/setting.json"):
        if times_now % 10 == 0:
            update_work_page(SITE, WORK_PAGE_NAME, WORK_TEMPLATE_NAME)
        page_list = get_pages_to_archive(SITE, WORK_PAGE_NAME)
        for page, pref in page_list.items():
            try:
                archive_page(page, site = SITE, work_page_name = WORK_PAGE_NAME, work_template_name = WORK_TEMPLATE_NAME, **pref)
            except  Exception as e:
                print(f"Skipped page '{page}', its prefercence is {pref}, and the error is {e}")
        time.sleep(600)
        times_now += 1
