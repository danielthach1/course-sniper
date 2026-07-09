import requests
import logging
import argparse
from apscheduler.schedulers.background import BackgroundScheduler
import time
import os
from datetime import datetime

from db import init_db, get_connection, get_active_watches, get_last_snapshot, save_snapshot, add_watch, remove_watch, list_watches, reset_db

from dotenv import load_dotenv
load_dotenv()



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

SOC_URL = "https://sis.rutgers.edu/soc/api/courses.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def send_discord_alert(section_id, year="2026", term="9", campus="NB"):
    # term codes:
    # 1 = Spring, 
    # 7 = Summer, 
    # 9 = Fall
    term_prefix = {"1": "9", "7": "7", "9": "1"}.get(term, "9")
    semester = f"{term_prefix}{year}"
    
    reg_url = f"https://sims.rutgers.edu/webreg/editSchedule.htm?login=cas&semesterSelection={semester}&indexList={section_id}"
    
    payload = {
        "content": f"Seat opened in section `{section_id}`! Register now:\n{reg_url}"
    }
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code != 204:
        logging.warning(f"Discord alert may have failed: {response.status_code} {response.text}")
    
def check_for_openings():
    conn = get_connection()
    watches = get_active_watches(conn)
    
    if not watches:
        logging.info("No active watches.")
        conn.close()
        return
    for watch in watches:
        section_id = watch["section_id"]
        subject = watch["subject"]
        logging.info(f"Checking section {section_id}...")   
        
        #Test: Force section open
        # send_discord_alert(section_id)
        # logging.info("Test alert sent.")
        
        #comment to test :
        current_status = fetch_open_status(section_id, subject) #a
        if current_status is None:
            logging.warning(f"Could not fetch status for {section_id}, skipping")
            continue
        
        last_status = get_last_snapshot(conn, section_id) 
        
        if not last_status and current_status:
            logging.info(f"Seat opened in {section_id}! Sending alert.")
            send_discord_alert(section_id)
            
        save_snapshot(conn, section_id, current_status)
        
    conn.close()

def run_scheduler():
    sched = BackgroundScheduler()
    sched.add_job(check_for_openings, 'interval', minutes=2, next_run_time=datetime.now())
    sched.start()
    logging.info("Scheduler started. Polling every 2 minutes. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        sched.shutdown(wait=False)

def parse_sections(course_json):
    results = []
    course_id = course_json["courseString"]
    title = course_json["title"]
    subject = course_json["subject"]
    
    for section in course_json["sections"]:
        instructors = ", ".join(i["name"] for i in section["instructors"])
        
        results.append({
            "course_id": course_id,
            "title": title,
            "subject": subject,
            "section_id": section["index"],
            "section_number": section["number"],
            "instructor": instructors,
            "open_status": section["openStatus"]
        })
    return results

def fetch_open_status(section_id, subject, year="2026", term="1", campus="NB"):
    try:
        response = requests.get(SOC_URL, params={
            "year": year,
            "term": term,
            "campus": campus,
            "subject": subject
        })
        response.raise_for_status()
        
        courses = response.json()
        
        for course in courses:
            for section_data in parse_sections(course):
                if section_data["section_id"] == section_id:
                    return section_data["open_status"]
                
        logging.warning(f"Section {section_id} not found in subject {subject} response.")
        return None
    
    except requests.RequestException as e:
        logging.error(f"API request failed {e}")
        return None



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rutgers Course Sniper")
    subparsers = parser.add_subparsers(dest="command")

    watch_parser = subparsers.add_parser("watch", help="Watch a section")
    watch_parser.add_argument("--section", required=True)
    watch_parser.add_argument("--subject", required=True)

    unwatch_parser = subparsers.add_parser("unwatch", help="Stop watching a section")
    unwatch_parser.add_argument("--section", required=True)

    subparsers.add_parser("start", help="Start the polling scheduler")
    subparsers.add_parser("list", help="List active watches")
    subparsers.add_parser("reset", help="Clear all watches and snapshots")

    args = parser.parse_args()

    init_db()

    if args.command == "watch":
        add_watch(args.section, args.subject)
    elif args.command == "unwatch":
        remove_watch(args.section)
    elif args.command == "start":
        run_scheduler()
    elif args.command == "list":
        list_watches()
    elif args.command == "reset":
        reset_db()
    else:
        parser.print_help()