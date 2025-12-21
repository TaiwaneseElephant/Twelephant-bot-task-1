import pywikibot
from pywikibot import textlib
import re
import time

find_signature_timestamp = lambda text : re.finditer(r"\d\d\d\d年\d\d?月\d\d?日 \([一二三四五六日]\) \d\d:\d\d \(UTC\)", text)

def find_all_match(regex, text):
    find_list = re.finditer(regex, text)
    result = []
    for i in find_list:
        result.append(i.group())
    return result

def archive(talk_page_name, year, month, num, talk_page, sections):
    text = f"\n\n{sections.sections[num].title}\n{sections.sections[num].content}"
    archive_page_name = f"{talk_page_name}/存檔/{year}年/{month}月"
    archive_page = pywikibot.Page(site, archive_page_name)
    archive_page.text += text
    archive_page.save(f"Archived from [[{talk_page_name}]] by Twelephant-bot")
    if sections.header.strip():
        new_page_text = [sections.header]
    else:
        new_page_text = []
    for i in range(len(sections.sections)):
        if i != num:
            new_page_text.append(f"{sections.sections[i].title}\n{sections.sections[i].content}")
    talk_page.text = "\n\n".join(new_page_text)
    talk_page.save(f"Archived to [[{archive_page_name}]] by Twelephant-bot")

def archive_page(page_name):
    talk_page = pywikibot.Page(site, page_name)
    sections = textlib.extract_sections(talk_page.text, site)
    for i in range(len(sections.sections)):
        if (signature_timestamp := find_signature_timestamp(sections.sections[i].content)):
            fail = False
            for j in signature_timestamp:
                j = j.group()
                for k in ["一", "二", "三", "四", "五", "六", "日"]:
                    j = j.replace(k, "a")
                time_then = time.strptime(j, "%Y年%m月%da (a) %H:%M (UTC)")
                time_diff = time.mktime(time.gmtime()) - time.mktime(time_then)
                if time_diff < (86400 * archive_day):
                    fail = True
                    break
            if fail:
                break
            else:
                archive(page_name, time_then.tm_year, time_then.tm_mon, i, talk_page, sections)
        else:
            break
        
def get_pages_needed_archive(text):
    page_list = re.finditer(r"{{User:Twelephant-bot/Archive_page|.*?}}", text)
    result = []
    for i in page_list:
        result.append("User talk:" + i.group().replace("* {{User:Twelephant-bot/Archive_page|","").replace("}}",""))
    return result

def send_welcome_massage(talk_page_name):
    talk_page = pywikibot.Page(site, talk_page_name)
    talk_page.text += "{{subst:User:Twelephant-bot/welcome message}}"
    talk_page.save("Welcoming user for using Twelephant-bot user talk page archive service by Twelephant-bot.")

def welcome_newcomers(new_page_list):
    with open("需要存檔的討論頁.txt", "r", encoding="utf-8") as f:
        old_page_list = str(f.read()).split("\n")
        welcome_list = []
        for i in new_page_list:
            if i not in old_page_list:
                input(i)
                send_welcome_massage(i)
    with open("需要存檔的討論頁.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(new_page_list))

def del_hide_text(text):
    hide_text = find_all_match(r"<!--.*?-->", text)
    result = text
    for i in hide_text:
        result = result.replace(i,"")
    return result
                
site = pywikibot.Site('wikipedia:zh')
archive_day = 10
times_limit = float("inf")
times_now = 0
while times_now < times_limit:
    work_page = pywikibot.Page(site, "User:Twelephant-bot/需要存檔的討論頁")
    text = work_page.text
    page_list = get_pages_needed_archive(del_hide_text(work_page.text))
    welcome_newcomers(page_list)
    for page in page_list:
        archive_page(page)
    times_now += 1
