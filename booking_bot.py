import time
import logging
import threading
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException, ElementClickInterceptedException, NoSuchElementException
import os
import shutil
import random
import pyautogui
from playsound import playsound
import subprocess

def setup_logger():
    """راه‌اندازی لاگر برای ثبت وقایع."""
    logger = logging.getLogger('booking_bot')
    logger.setLevel(logging.INFO)
    if logger.hasHandlers():
        logger.handlers.clear()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    try:
        file_handler = logging.FileHandler('booking_log.txt', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Error setting up file logger: {e}")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger

logger = setup_logger()
slot_check_timer = None

def kill_chrome_processes(logger):
    """بستن تمام پروسه‌های کروم و کروم‌درایور."""
    logger.info("Attempting to kill all Chrome and Chromedriver processes...")
    try:
        if os.name == 'nt': # For Windows
            subprocess.run('taskkill /F /IM chrome.exe /T', check=False, shell=True, capture_output=True)
            subprocess.run('taskkill /F /IM chromedriver.exe /T', check=False, shell=True, capture_output=True)
        else: # For macOS/Linux
            subprocess.run("pkill -f 'Google Chrome'", shell=True, check=False)
            subprocess.run("pkill -f 'chromedriver'", shell=True, check=False)
        logger.info("Kill command executed.")
    except Exception as e:
        logger.error(f"An error occurred while trying to kill Chrome processes: {e}")

def play_sound_in_thread(sound_file, disable_sound=False):
    """پخش فایل صوتی در یک ترد جداگانه برای جلوگیری از بلاک شدن برنامه."""
    if disable_sound:
        return
    def target():
        try:
            if os.path.exists(sound_file):
                playsound(sound_file)
            else:
                logger.warning(f"Sound file not found: {sound_file}")
        except Exception as e:
            logger.error(f"Could not play sound file '{sound_file}'. Error: {e}")
    threading.Thread(target=target, daemon=True).start()

def play_error_sound():
    """پخش صدای خطا."""
    logger.warning("No slot activity detected for 10 minutes. Playing error sound.")
    play_sound_in_thread('error.mp3')

def reset_slot_check_timer(disable_error_sound):
    """ریست کردن تایمر بررسی اسلات."""
    global slot_check_timer
    if slot_check_timer and slot_check_timer.is_alive():
        slot_check_timer.cancel()
    if not disable_error_sound:
        slot_check_timer = threading.Timer(600, play_error_sound) # 10 minutes
        slot_check_timer.daemon = True
        slot_check_timer.start()

def click_captcha_area(logger, x_min, x_max, y_min, y_max, captcha_delay, stop_event):
    """
    تابع یکپارچه برای کلیک روی ناحیه کپچا با استفاده از مختصات ورودی.
    """
    try:
        logger.info(f"CAPTCHA detected. Waiting for {captcha_delay} seconds before clicking...")
        for _ in range(captcha_delay):
            if stop_event.is_set(): return False
            time.sleep(1)

        if stop_event.is_set(): return False

        x = random.randint(x_min, x_max)
        y = random.randint(y_min, y_max)

        logger.info(f"Moving mouse to ({x}, {y}) for CAPTCHA click.")
        pyautogui.moveTo(x, y, duration=random.uniform(0.5, 1.5))
        pyautogui.click()
        logger.info(f"CAPTCHA clicked. Waiting 10 seconds to proceed.")
        time.sleep(10)
        return True
    except Exception as e:
        logger.error(f"An error occurred during the CAPTCHA click: {e}")
        return False

def run_booking_process(email, password, desired_month, stop_event, mode, refresh_delay, x_min, x_max, y_min, y_max, captcha_delay, captcha_enabled, slot_selection_strategy, disable_error_sound, disable_slot_sound):
    logger.info("="*60)
    logger.info(f"🚀 Starting process for: {email} | Mode: {mode}")
    reset_slot_check_timer(disable_error_sound)

    profile_dir = os.path.join(os.getcwd(), 'chrome_profile', email)
    driver_path = os.path.join(os.getcwd(), 'chromedriver.exe')

    while not stop_event.is_set():
        driver = None
        try:
            # Clean up before starting
            kill_chrome_processes(logger)
            if os.path.exists(profile_dir):
                shutil.rmtree(profile_dir, ignore_errors=True)
                logger.info(f"Cleared profile directory for {email}.")
            os.makedirs(profile_dir, exist_ok=True)
            
            BASE_URL = "https://visas-de.tlscontact.com/en-us/country/ir/vac/irTHR2de"
            SESSION_TIMEOUT_TITLE = "Germany visa application centre | TLScontact"

            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.5

            options = uc.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument(f"--user-data-dir={profile_dir}")
            options.page_load_strategy = 'eager'
            prefs = { "credentials_enable_service": False, "profile.password_manager_enabled": False }
            options.add_experimental_option("prefs", prefs)

            driver = uc.Chrome(options=options, use_subprocess=True, driver_executable_path=driver_path)
            driver.maximize_window()
            driver.set_page_load_timeout(60)
            wait = WebDriverWait(driver, 20)
            fast_wait = WebDriverWait(driver, 7)
            
            driver.get(BASE_URL)

            if "Access denied" in driver.title:
                logger.critical(f"ACCESS DENIED (Error 1015) for {email}. IP might be banned.")
                logger.info("Stopping applicant, killing all Chrome processes, and clearing the entire chrome_profile directory.")
                kill_chrome_processes(logger)
                main_profile_folder = os.path.join(os.getcwd(), 'chrome_profile')
                if os.path.exists(main_profile_folder):
                    shutil.rmtree(main_profile_folder, ignore_errors=True)
                    logger.info("Entire 'chrome_profile' directory has been deleted.")
                return False

            if "Just a moment..." in driver.title and captcha_enabled:
                click_captcha_area(logger, x_min, x_max, y_min, y_max, captcha_delay, stop_event)

            try:
                login_wait = WebDriverWait(driver, 15)
                login_wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href='/en-us/login']"))).click()
                logger.info("Entering credentials...")
                wait.until(EC.presence_of_element_located((By.ID, "email-input-field"))).send_keys(email)
                driver.find_element(By.ID, "password-input-field").send_keys(password)
                driver.find_element(By.ID, "btn-login").click()
                logger.info("Logged in successfully.")
            except TimeoutException:
                logger.warning("Login button not found or failed. Restarting.")
                continue
            
            if "Attention Required! | Cloudflare" in driver.title:
                logger.warning("Cloudflare block page detected. Applying workaround...")
                driver.get(BASE_URL)
                try:
                    profile_icon_xpath = "(//div[@role='listitem'])[last()]"
                    profile_icon = wait.until(EC.element_to_be_clickable((By.XPATH, profile_icon_xpath)))
                    driver.execute_script("arguments[0].click();", profile_icon)
                    
                    my_application_link = wait.until(EC.element_to_be_clickable((By.ID, "my-application")))
                    driver.execute_script("arguments[0].click();", my_application_link)
                    logger.info("Navigated to dashboard via profile menu.")
                except Exception as e:
                    logger.error(f"Failed to navigate to dashboard after login. Restarting process. Error: {e}")
                    continue
           
            logger.info("Navigating to dashboard...")
            # Use a more robust selector that finds the first button, regardless of how many there are.
            first_select_button = wait.until(EC.presence_of_element_located((By.XPATH, "(//button[@data-testid='btn-select-group'])[1]")))
            driver.execute_script("arguments[0].click();", first_select_button)
            logger.info("Clicked the first 'Select' button.")

            logger.info("Group selected. Moving to booking page...")

            try:
                time.sleep(2) # Wait for cookie banner animation
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'osano-cm-accept')]"))).click()
                logger.info("Cookie banner accepted.")
            except TimeoutException:
                pass 
            
            booking_successful = False
            
            logger.info("Using 'Calendar Page' refresh method.")
            try:
                book_appointment_btn = wait.until(EC.element_to_be_clickable((By.ID, "book-appointment-btn")))
                driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", book_appointment_btn)
            except Exception:
                book_appointment_btn = driver.find_element(By.ID, "book-appointment-btn")
                driver.execute_script("arguments[0].click();", book_appointment_btn)
            
            wait.until(EC.url_contains("appointment-booking"))
            logger.info("✅ Calendar page loaded successfully.")
            
            if desired_month == 'next_month':
                try:
                    logger.info("Attempting to navigate to the next month...")
                    next_month_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-testid='btn-next-month-available']")))
                    driver.execute_script("arguments[0].click();", next_month_btn)
                    time.sleep(1)
                    logger.info("Successfully navigated to the next month.")
                except Exception as e:
                    logger.warning(f"Could not navigate to next month. Continuing with current. Error: {e}")
            
            while not stop_event.is_set() and not booking_successful:
                reset_slot_check_timer(disable_error_sound)
                
                if driver.title == SESSION_TIMEOUT_TITLE:
                    logger.warning("Session timeout detected (redirected to home page). Restarting the process.")
                    break # This will cause the outer loop to restart the process
                
                if "Just a moment..." in driver.title and captcha_enabled:
                    click_captcha_area(logger, x_min, x_max, y_min, y_max, captcha_delay, stop_event)
                if stop_event.is_set(): break

                try:
                    if book_first_available_slot(driver, wait, fast_wait, stop_event, slot_selection_strategy, logger, disable_slot_sound):
                        booking_successful = True
                        break
                    else:
                        if "appointment-booking" in driver.current_url:
                            logger.info("All found slots were taken. Refreshing.")
                            driver.refresh()
                            time.sleep(refresh_delay)
                except TimeoutException:
                    if "appointment-booking" in driver.current_url:
                        logger.info(f"No slots found. Refreshing in {refresh_delay} seconds...")
                        for _ in range(refresh_delay):
                            if stop_event.is_set(): break
                            time.sleep(1)
                        if stop_event.is_set(): break
                        driver.refresh()
                    else:
                        logger.warning(f"Not on calendar page. Current URL: {driver.current_url}. Restarting process.")
                        break
            
            if stop_event.is_set():
                 logger.warning(f"Booking process for {email} was stopped by the user.")
                 if slot_check_timer: slot_check_timer.cancel()
                 return False

            if booking_successful:
                try:
                    logger.info("Finalizing booking...")
                    confirm_order_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-confirm-order-summary")))
                    driver.execute_script("arguments[0].click();", confirm_order_btn)
                    
                    go_to_payment_btn = wait.until(EC.element_to_be_clickable((By.ID, "go-to-tls-payment-0")))
                    driver.execute_script("arguments[0].click();", go_to_payment_btn)
                    logger.info("Clicked 'Proceed to checkout'.")

                    try:
                        ok_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'modal-footer')]//button[normalize-space()='Ok']")))
                        driver.execute_script("arguments[0].click();", ok_button)
                        logger.info("Clicked 'Ok' on the confirmation modal.")
                    except TimeoutException:
                        pass # No modal
                    
                    logger.info("Looking for 'Pay later' option...")
                    pay_later_div_xpath = "//h3[normalize-space()='Pay later in our office']/ancestor::div[contains(@class, 'payment-option')]"
                    pay_later_element = wait.until(EC.presence_of_element_located((By.XPATH, pay_later_div_xpath)))
                    
                    logger.info("Using ActionChains to click 'Pay later'.")
                    actions = ActionChains(driver)
                    actions.move_to_element(pay_later_element).click().perform()
                    logger.info("Successfully clicked on 'Pay later in our office' option.")

                    confirm_submit_btn = wait.until(EC.element_to_be_clickable((By.ID, "confirm_submit")))
                    driver.execute_script("arguments[0].click();", confirm_submit_btn)
                    
                    logger.info("Waiting for the final confirmation page to load...")
                    WebDriverWait(driver, 30).until(EC.title_contains("My Application"))
                    time.sleep(2)

                    logger.info("🎉🎉 APPOINTMENT BOOKED SUCCESSFULLY! 🎉🎉")
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    screenshot_filename = f"APPOINTMENT_{email.split('@')[0]}_{timestamp}.png"
                    driver.save_screenshot(screenshot_filename)
                    logger.info(f"📸 Screenshot saved as: {screenshot_filename}")
                    
                    if slot_check_timer: slot_check_timer.cancel()
                    return True # Indicate success
                except Exception as e:
                    logger.error(f"Error during finalization for {email}: {e}", exc_info=True)
                    logger.warning("Browser will remain open for manual completion.")
                    time.sleep(3600)
                    if slot_check_timer: slot_check_timer.cancel()
                    return False # Indicate failure

        except WebDriverException as e:
            if stop_event.is_set():
                logger.warning(f"Process for {email} was stopped. Exiting.")
                break
            logger.error(f"WebDriver crashed for {email}. Restarting... Error: {e}")
            time.sleep(5)
            continue
        except Exception as e:
            if stop_event.is_set(): break
            logger.error(f"BOOKING FAILED for {email}. Unexpected error: {type(e).__name__} - {e}", exc_info=True)
            time.sleep(10)
            continue
            
        finally:
            if driver:
                driver.quit() # Ensure browser closes
            logger.info(f"Browser session for {email} completely terminated.")
    
    if slot_check_timer: slot_check_timer.cancel()
    logger.info(f"Process for {email} has been fully terminated.")
    return False

def book_first_available_slot(driver, wait, fast_wait, stop_event, slot_selection_strategy, logger, disable_slot_sound):
    """
    Helper function to find, sort, and attempt to book an available slot on the calendar page.
    """
    SLOT_XPATH = "//button[@data-testid='btn-available-slot']"
    logger.info("Searching for available slots on calendar...")
    available_slots = fast_wait.until(EC.presence_of_all_elements_located((By.XPATH, SLOT_XPATH)))
    
    logger.info(f"Found {len(available_slots)} available slots! Attempting to book one.")
    play_sound_in_thread('beep.mp3', disable_sound=disable_slot_sound)

    if slot_selection_strategy == 'fastest':
        available_slots.sort(key=lambda x: x.text)
        slots_to_try = available_slots[:min(3, len(available_slots))]
        random.shuffle(slots_to_try)
    elif slot_selection_strategy == 'latest':
        available_slots.sort(key=lambda x: x.text, reverse=True)
        slots_to_try = available_slots[:min(3, len(available_slots))]
        random.shuffle(slots_to_try)
    else: # random (default)
        random.shuffle(available_slots)
        slots_to_try = available_slots

    for slot in slots_to_try:
        if stop_event.is_set(): return False
        try:
            slot_text = slot.text
            logger.info(f"Attempting to book slot: {slot_text}")
            driver.execute_script("arguments[0].click();", slot)
            book_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Book your appointment')]")))
            driver.execute_script("arguments[0].click();", book_btn)
            
            try:
                # After clicking book, wait for one of the elements that indicates success
                WebDriverWait(driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.ID, "btn-confirm-order-summary")),
                        EC.title_contains("My Application")
                    )
                )
                logger.info("Successfully clicked 'Book' and proceeded to the summary or confirmation page.")
                return True # This is a successful booking attempt
            except TimeoutException:
                if "Welcome to TLScontact Payment" in driver.title:
                    logger.warning("Payment error page detected. Clicking 'Try Again'.")
                    try_again_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'workflow/payment')]")))
                    driver.execute_script("arguments[0].click();", try_again_link)
                    
                    logger.info("Clicked 'Try Again'. Waiting to land on a valid page...")
                    WebDriverWait(driver, 20).until(
                        EC.any_of(
                            EC.element_to_be_clickable((By.ID, "btn-confirm-order-summary")),
                            EC.element_to_be_clickable((By.ID, "go-to-tls-payment-0")),
                            EC.element_to_be_clickable((By.ID, "confirm_submit")),
                             EC.title_contains("My Application")
                        )
                    )
                    logger.info("Landed on a valid page after 'Try Again'. Continuing finalization.")
                    return True
                else:
                    # If it's not the payment error page, the slot was likely taken.
                    raise
        except (TimeoutException, ElementClickInterceptedException):
            logger.warning(f"Slot {slot_text} was likely taken or booking failed. Trying next.")
            continue
        except Exception as e:
            logger.error(f"An error occurred while booking slot {slot_text}: {e}")
            continue
            
    return False # No slot was successfully booked