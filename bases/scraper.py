from linkedin_scraper import Person, actions
from selenium import webdriver

# Set up the Chrome driver (make sure chromedriver.exe is in your PATH or specify the path)
driver = webdriver.Chrome()

# Log in to LinkedIn (replace with your credentials)
actions.login(driver, "crce.10281.ceb@gmail.com", "Samsung@6ymS")

# Replace with the LinkedIn profile URL you want to scrape
profile_url = "https://www.linkedin.com/in/prakriti-soni-4baa72328/"

# Scrape the profile
person = Person(profile_url, driver=driver)

# Print some data
print("Name:", person.name)
print("Experiences:", person.experiences)
print("Educations:", person.educations)
print("Interests:", person.interests)

# Close the driver
driver.quit()