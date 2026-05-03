import requests
import re
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import urllib.parse
import difflib

class ActionFetchDepartmentInfo(Action):
    def name(self) -> Text:
        # Matches the exact name in your domain.yml
        return "action_fetch_department_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # 👉 V2: GRAB ALL THE NEW ENTITIES
        query_name = tracker.get_slot("department_name")
        level_slot = tracker.get_slot("level")
        semester_slot = tracker.get_slot("semester")
        course_code = tracker.get_slot("course_code")
        
        current_intent = tracker.latest_message['intent'].get('name')
        user_text = tracker.latest_message.get('text', '').lower()

        # Python Fallback: If Rasa missed the slot, use Python Regex to find "CSC 411"
        # ==========================================
        # 0. FAST-TRACK FOR SPECIFIC COURSES (V2.4 Final)

        extracted_code = None
        
        # 1. Find ALL matches in the sentence, not just the first one!
        matches = re.findall(r'\b[a-zA-Z]{3}\s?\d{3}\b', user_text)
        # 👉 THE UPGRADED IGNORE LIST (Stop Words)
        ignore_prefixes = ["THE", "FOR", "AND", "ANY", "ARE", "ALL", "HOW", "WHO", "CAN", "YOU", "NOT", "BUT"]
        
        for m in matches:
            potential_code = m.upper().replace(" ", "")
            
            # Extract just the first 3 letters to check if it's a common English word
            first_three_letters = potential_code[:3]
            
            # 2. Ignore noise. If it's a REAL code, lock it in and stop searching.
            if first_three_letters not in ignore_prefixes:
                extracted_code = potential_code
                break

        # 3. Only enter the Fast-Track if we KNOW they are asking for a specific course
        if extracted_code or current_intent == "ask_specific_course":
            
            if extracted_code:
                try:
                    # ATTEMPT 1: Try the URL without a space (e.g., CSC411)
                    url = f"http://127.0.0.1:8000/api/course/{extracted_code}/"
                    response = requests.get(url)
                    
                    # ATTEMPT 2: If Django says 404 Not Found, inject a space and try again!
                    if response.status_code != 200:
                        code_with_space = extracted_code[:3] + " " + extracted_code[3:] # Turns "CSC411" into "CSC 411"
                        url_with_space = f"http://127.0.0.1:8000/api/course/{code_with_space}/"
                        response = requests.get(url_with_space)
                    
                    # 4. Now check if EITHER of those attempts worked
                    if response.status_code == 200:
                        data = response.json()
                        compulsory_text = "Compulsory" if data.get('is_compulsory') else "Elective"
                        dispatcher.utter_message(
                            text=f"📚 **{data.get('course_code')} - {data.get('title')}**\n"
                                 f"• Units: {data.get('credit_units')}\n"
                                 f"• Semester: {data.get('semester', '1st')} Semester\n"
                                 f"• Status: {compulsory_text}"
                        )
                        return [SlotSet("course_code", None), SlotSet("last_intent", None)]
                    
                    else:
                        dispatcher.utter_message(text=f"I couldn't find the course '{extracted_code}' or '{code_with_space}' in the database. Are you sure the spelling is correct?")
                        return [SlotSet("course_code", None), SlotSet("last_intent", None)]
                        
                except requests.exceptions.RequestException:
                    dispatcher.utter_message(text="My course database is currently offline.")
                    return []
            
            else:
                dispatcher.utter_message(text="I see you're asking about a course, but I didn't catch the exact course code (e.g., 'CSC 411'). Could you provide it?")
                return [SlotSet("course_code", None), SlotSet("last_intent", None)]

        # ==========================================
        # 2. THE MULTI-GOAL SCANNER (Upgraded for V2)
        # ==========================================
        detected_goals = []
        clean_text = user_text.replace(',', '').replace('.', '').replace('?', '')
        clean_words = clean_text.split()
        
        # V1 Goals
        if "hod" in clean_words or "head of" in user_text:
            detected_goals.append("ask_hod")
        if "email" in user_text or "contact" in user_text or "number" in user_text:
            detected_goals.append("ask_department_contact")
        if "faculty" in user_text: 
            detected_goals.append("ask_department_faculty")
        if current_intent in ["ask_jamb_requirements", "ask_general_requirements"] or any(word in user_text for word in ["jamb", "cut off", "cutoff", "post utme", "screening"]):
            detected_goals.append("ask_jamb")
        if current_intent in ["ask_olevel_requirements", "ask_general_requirements"] or any(word in user_text for word in ["waec", "neco", "sittings", "o level"]): 
            detected_goals.append("ask_olevel")
        if current_intent == "ask_direct_entry" or any(word in user_text for word in ["direct entry", "de ", "jupeb", "ond"]):
            detected_goals.append("ask_direct_entry")
        if current_intent == "ask_for_transfer" or any(word in user_text for word in ["transfer", "cgpa"]):
            detected_goals.append("ask_for_transfer")
        if current_intent == "ask_fees" or any(word in user_text for word in ["fees", "money", "pay", "cost", "tuition", "hostel"]):
            detected_goals.append("ask_fees")
        if current_intent == "ask_scholarships" or any(word in user_text for word in ["scholarship", "discount"]):
            detected_goals.append("ask_scholarships")
            
        # V2 Goals (Levels, Reps, Advisors, Semesters)
        if current_intent == "ask_course_advisor" or "advisor" in user_text:
            detected_goals.append("ask_course_advisor")
        if current_intent == "ask_course_rep" or "rep" in user_text or "representative" in user_text:
            detected_goals.append("ask_course_rep")
        if current_intent in ["ask_level_courses", "ask_semester_courses"] or "courses" in user_text:
            detected_goals.append("ask_courses")
            
        if "info" in user_text or "details" in user_text or ("about" in user_text and not detected_goals):
            detected_goals.append("ask_department_info")

        # ==========================================
        # 3. RETRIEVE THE SAVED GOAL / ASK FOR DEPT
        # ==========================================
        saved_goal_string = tracker.get_slot("last_intent")
        if saved_goal_string and not detected_goals and current_intent in ["inform", "ask_department_info", "nlu_fallback"]:
            active_goals = saved_goal_string.split(",")
        else:
            active_goals = detected_goals if detected_goals else [current_intent]

        if not query_name:
            if current_intent == "nlu_fallback" and not detected_goals:
                dispatcher.utter_message(response="utter_default")
                return [SlotSet("last_intent", None)]
            
            dispatcher.utter_message(response="utter_ask_item_name")
            return [SlotSet("last_intent", ",".join(active_goals))]

       # ==========================================
        # 4. FETCH FROM DJANGO & BUILD RESPONSE
        # ==========================================
        try:
            # 👉 BUG 1 FIX: Safely encode spaces (e.g., "Computer Science" -> "Computer%20Science")
            safe_query = urllib.parse.quote(query_name)
            
            # Hitting the main Department doorway with the safe URL
            url = f"http://127.0.0.1:8000/api/department/{safe_query}/"
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                dept_name = data.get('name', query_name.title()) 
                response_messages = []
                
               
                # V2: Extract target level data (BULLETPROOF STRING MATCHING)
                target_level_data = None
                if level_slot:
                    # Clean the slot (e.g., turn "400L" or "400 level" into just "400")
                    clean_level = str(level_slot).lower().replace("l", "").replace("level", "").strip()
                    
                    for l in data.get("levels", []):
                        # Force Django's integer into a string for a perfect match
                        if str(l.get("level")) == clean_level:
                            target_level_data = l
                            break

                if not active_goals or active_goals == ["inform"]:
                    active_goals = ["ask_department_info"]

                for goal in active_goals:
                    # -- V1 CORE GOALS --
                    if goal == "ask_hod":
                        response_messages.append(f"The Head of Department for {dept_name} is {data.get('head_of_department')}. 👤")
                    elif goal == "ask_department_faculty":
                        response_messages.append(f"The {dept_name} department is situated within the Faculty of {data.get('faculty', {}).get('name', 'Unknown')}. 🏛️")
                    elif goal == "ask_department_info":
                        response_messages.append(f"Here is what you need to know about {dept_name}:\n{data.get('about')}")
                    
                    # ==========================================
                    # -- V2 ADMISSION GOALS --
                    # ==========================================
                    elif goal == "ask_fees":
                        admission = data.get('admission_info', {})
                        if admission:
                            response_messages.append(f"The total school fees for {dept_name} are {admission.get('total_school_fees', 'not specified')}. The acceptance fee is {admission.get('acceptance_fee', 'not specified')}. 💳")
                    
                    elif goal == "ask_jamb":
                        admission = data.get('admission_info', {})
                        if admission:
                            response_messages.append(f"The JAMB cut-off is {admission.get('jamb_cutoff_mark', 'not specified')} and subjects are: {admission.get('jamb_subject_combination', 'not specified')}.")
                    
                    elif goal == "ask_olevel":
                        admission = data.get('admission_info', {})
                        if admission:
                            response_messages.append(f"For your O'Levels, you need: {admission.get('compulsory_olevel_subjects', 'not specified')}. 📚")

                    # 👉 NEW V2 ADDITIONS START HERE
                    elif goal == "ask_admission_requirements":
                        admission = data.get('admission_info', {})
                        if admission:
                            jamb_score = admission.get('jamb_cutoff_mark', '160')
                            jamb_subs = admission.get('jamb_subject_combination', 'Not specified')
                            waec_subs = admission.get('compulsory_olevel_subjects', 'Not specified')
                            # NOTE: Make sure 'direct_entry_requirements' matches your Django models.py!
                            de_reqs = admission.get('direct_entry_requirements', 'ND/HND/IJMB/JUPEB in relevant fields.')
                            
                            response_messages.append(
                                f"🎓 **Admission Requirements for {dept_name}**\n\n"
                                f"**1. JAMB (UTME):**\n"
                                f"• Cut-off: {jamb_score}\n"
                                f"• Subjects: {jamb_subs}\n\n"
                                f"**2. O'Level (WAEC/NECO):**\n"
                                f"• 5 Credits in: {waec_subs}\n\n"
                                f"**3. Direct Entry (DE):**\n"
                                f"• {de_reqs}"
                            )
                        else:
                            response_messages.append(f"I don't have the admission requirements for {dept_name} right now.")

                    elif goal == "ask_direct_entry":
                        admission = data.get('admission_info', {})
                        if admission:
                            # Using your exact Django boolean and text keys!
                            if admission.get('accepts_direct_entry'):
                                de_reqs = admission.get('de_minimum_qualification', 'valid OND/JUPEB/IJMB')
                                response_messages.append(f"Yes! For Direct Entry into {dept_name}, you need: {de_reqs} 🎓")
                            else:
                                response_messages.append(f"Sorry, {dept_name} does not accept Direct Entry students at this time.")

                    elif goal == "ask_for_transfer":
                        admission = data.get('admission_info', {})
                        if admission:
                            # Using your exact transfer keys!
                            if admission.get('accepts_transfers'):
                                cgpa = admission.get('minimum_transfer_cgpa', 'specified by the department')
                                response_messages.append(
                                    f"🔄 **Transferring to {dept_name}:**\n"
                                    f"Yes, transfers are accepted! You will need a minimum of {cgpa}.\n"
                                    f"Ensure you also have your official transcripts and a completed transfer form from the Admissions Office."
                                )
                            else:
                                response_messages.append(f"Sorry, {dept_name} does not currently accept transfer students.")
                    # -- V2 LEVEL & COURSE GOALS --
                    elif goal == "ask_course_advisor":
                        if target_level_data:
                            response_messages.append(f"The Course Advisor for {level_slot}L {dept_name} is {target_level_data.get('course_advisor')}. 👨‍🏫")
                        else:
                            response_messages.append(f"I don't have the course advisor specifically for {level_slot}L right now, or you didn't specify a level.")
                            
                    elif goal == "ask_course_rep":
                        if target_level_data:
                            # 👉 THE FIX: Changed to 'course_rep_name' to match Django!
                            rep_name = target_level_data.get('course_rep_name', 'not assigned yet')
                            
                            # Safely check for a phone number (just in case it doesn't exist in Django)
                            rep_phone = target_level_data.get('course_rep_phone') 
                            
                            if rep_phone:
                                response_messages.append(f"The Class Representative for {level_slot}L {dept_name} is {rep_name} ({rep_phone}). 📱")
                            else:
                                response_messages.append(f"The Class Representative for {level_slot}L {dept_name} is {rep_name}. 📱")
                        else:
                            response_messages.append(f"Please specify a level (e.g., 200L) so I can find the right class rep for {dept_name}.")
                    elif goal == "ask_courses":
                        if target_level_data:
                            courses = target_level_data.get("courses", [])
                            
                            # 👉 THE NEW TYPO CATCHER
                            actual_semester = semester_slot
                            if not actual_semester:
                                if any(w in user_text for w in ["1st", "first", "fist"]): # fist catches typos!
                                    actual_semester = "1st"
                                elif any(w in user_text for w in ["2nd", "second", "fsecond"]): # catches your exact typo!
                                    actual_semester = "2nd"

                            # 👉 THE SAFE FILTERING
                            if actual_semester:
                                # Safe filter (handles if Django saves "1st" or "First")
                                if actual_semester == "1st":
                                    courses = [c for c in courses if "1" in str(c.get("semester")) or "first" in str(c.get("semester")).lower()]
                                else:
                                    courses = [c for c in courses if "2" in str(c.get("semester")) or "second" in str(c.get("semester")).lower()]
                                    
                                response_messages.append(f"Here are the {actual_semester} Semester courses for {level_slot}L {dept_name}:\n")
                            else:
                                response_messages.append(f"Here are ALL the courses for {level_slot}L {dept_name}:\n")
                            
                            # 👉 PRINTING THE RESULTS
                            for c in courses:
                                status = "Compulsory" if c.get("is_compulsory") else "Elective"
                                response_messages.append(f"- {c.get('course_code')}: {c.get('title')} ({c.get('credit_units')} Units, {status})")
                                
                            if not courses:
                                response_messages.append("No courses mapped for this semester/level yet.")
                        else:
                            response_messages.append(f"To see courses for {dept_name}, please tell me which level you are in (e.g., 'What are the 100L courses?').")
                final_reply = "\n".join(response_messages)
                
                if not final_reply.strip():
                    final_reply = f"I found the {dept_name} department. What specific information would you like to know?"
                    
                dispatcher.utter_message(text=final_reply)
                
                # 👉 V2: SAVING THE NEW CONTEXT SLOTS
                return [
                    SlotSet("department_name", dept_name),
                    SlotSet("last_intent", ",".join(active_goals))
                ]
                
            else:
                dispatcher.utter_message(text=f"I couldn't find any records for '{query_name}'. Could you check the spelling?")
                return [SlotSet("department_name", None), SlotSet("last_intent", None)]
                
        except requests.exceptions.RequestException:
            dispatcher.utter_message(text="I'm having trouble connecting to the school database. Please ensure Django is running on Port 8000!")
            return []

# ==========================================
# 🆕 NEW: THE FACULTY ACTION SCRIPT
# ==========================================
class ActionFetchFacultyInfo(Action):
    def name(self) -> Text:
        return "action_fetch_faculty_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # 1. Grab Rasa's memory and the actual text the user typed
        faculty_query = tracker.get_slot("faculty_name")
        current_intent = tracker.latest_message['intent'].get('name') 
        user_text = tracker.latest_message.get('text', '') 

        # ==========================================
        # 🧠 THE AGGRESSIVE MEMORY OVERRIDE
        # ==========================================
        # This scans the text for "faculty of [ANYTHING]" and forces it into the slot.
        # This stops the bot from holding onto "Computing" when you ask for "Robotics".
        match = re.search(r"faculty\s+(?:of\s+)?([a-zA-Z\s]+)", user_text, re.IGNORECASE)
        
        if match:
            potential_new_faculty = match.group(1).strip()
            if len(potential_new_faculty) >= 3: 
                faculty_query = potential_new_faculty

        if not faculty_query:
            dispatcher.utter_message(text="Which faculty would you like to know about? (e.g., Faculty of Computing)")
            return []

        # ==========================================
        # 🛑 THE HARD BLOCK & AUTO-CORRECT
        # ==========================================
        # ONLY list what is actually in your Django DB right now!
        valid_faculties = ["Computing"] 
        
        # Check if what they asked for is in the list (with a little room for typos)
        matches = difflib.get_close_matches(faculty_query.title(), valid_faculties, n=1, cutoff=0.7)
        
        if matches:
            # It's a real faculty! Lock in the correct spelling.
            faculty_query = matches[0] 
        else:
            # 🚨 KILL IT HERE! It's a fake/missing faculty (like "Robotics").
            # Wipe the memory and warn the user. Do NOT talk to Django.
            dispatcher.utter_message(text=f"I couldn't find '{faculty_query}' in the university database. Please check the spelling or ask about an available faculty.")
            return [SlotSet("faculty_name", None)]

        # ==========================================
        # 🛡️ THE URL ENCODER (Handles Spaces)
        # ==========================================
        safe_query = urllib.parse.quote(faculty_query)

        # ==========================================
        # 🌐 FETCH FROM DJANGO
        # ==========================================
        try:
            url = f"http://127.0.0.1:8000/api/faculty/{safe_query}/"
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                fac_name = data.get('name', faculty_query.title())
                dean = data.get('dean', 'Not specified')
                about = data.get('about', '')
                contact_email = data.get('contact_email', 'No email listed.') 

                # 🧠 THE MULTI-GOAL SCANNER FOR FACULTIES
                if current_intent == "ask_about_dean":
                    dispatcher.utter_message(text=f"The Dean of the Faculty of {fac_name} is {dean}. 👨‍🏫")
                
                elif current_intent == "ask_about_faculty_contact":
                    dispatcher.utter_message(text=f"You can contact the Faculty of {fac_name} at: {contact_email} 📧")
                
                else:
                    # Default: General Faculty Info
                    dept_list = data.get('departments', [])
                    dept_strings = [f"• {d.get('name')}" for d in dept_list]
                    depts_formatted = "\n".join(dept_strings) if dept_strings else "No departments listed yet."

                    reply = (
                        f"🏛️ **Faculty of {fac_name}**\n\n"
                        f"**Dean:** {dean}\n\n"
                        f"{about}\n\n"
                        f"**Departments in this Faculty:**\n"
                        f"{depts_formatted}"
                    )
                    dispatcher.utter_message(text=reply)

                return [SlotSet("faculty_name", fac_name)]
                
            else:
                dispatcher.utter_message(text=f"I couldn't find a faculty named '{faculty_query}'. Please check the spelling!")
                return [SlotSet("faculty_name", None)]
                
        except requests.exceptions.RequestException:
            dispatcher.utter_message(text="I'm having trouble connecting to the university database right now. Ensure Django is running on Port 8000!")
            return []