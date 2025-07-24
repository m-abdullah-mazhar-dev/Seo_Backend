from venv import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# def get_paa_questions(query):
#     """
#     Fetches 'People Also Ask' questions from Google search results for a given query.
#     Returns a list of data-q values (questions).
#     """
#     options = Options()
#     options.add_argument("--headless=new")
#     options.add_argument("--disable-gpu")
#     options.add_argument("--window-size=1920,1080")
#     options.add_argument("--disable-blink-features=AutomationControlled")
#     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
#     options.add_experimental_option("excludeSwitches", ["enable-automation"])
#     options.add_experimental_option('useAutomationExtension', False)

#     driver = None
#     paa_questions = []

#     try:
#         driver = webdriver.Chrome(options=options)
#         driver.get(f"https://www.google.com/search?q={query}")

#         WebDriverWait(driver, 10).until(
#             EC.presence_of_element_located((By.XPATH, '//div[@class="LQCGqc"]'))
#         )

#         question_divs = driver.find_elements(
#             By.XPATH,
#             '//div[@class="LQCGqc"]/div[@jsname="yEVEwb"]//div[@class="wQiwMc related-question-pair"]'
#         )

#         for div in question_divs:
#             data_q = div.get_attribute("data-q")
#             if data_q:
#                 paa_questions.append(data_q)
     
    
#     except Exception as e:
#         print(f"Error occurred: {e}")
#     finally:
#         if driver:
#             driver.quit()

#     return paa_questions


def get_paa_questions(query):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = None
    paa_questions = []

    try:
        driver = webdriver.Chrome(options=options)
        driver.get(f"https://www.google.com/search?q={query}")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@class="LQCGqc"]'))
        )

        question_divs = driver.find_elements(
            By.XPATH,
            '//div[@class="LQCGqc"]/div[@jsname="yEVEwb"]//div[@class="wQiwMc related-question-pair"]'
        )

        for div in question_divs:
            data_q = div.get_attribute("data-q")
            if data_q:
                paa_questions.append(data_q)
     
    except Exception as e:
        logger.error(f"Error occurred while fetching PAA questions: {str(e)}")
    finally:
        if driver:
            driver.quit()

    return paa_questions

if __name__ == "__main__":
    query = "freelance job"
    questions = get_paa_questions(query)
    print("Extracted Questions:")
    for q in questions:
        print("-", q)
