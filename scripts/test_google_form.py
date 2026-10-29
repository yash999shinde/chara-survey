from playwright.sync_api import sync_playwright

FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSfh73QStzk0cZ6gvqRHZWG9V4yGsBv3tx2Z6P3WroXS97XxHQ/viewform"
)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(FORM_URL, wait_until="domcontentloaded", timeout=60000)

    print("Google Form opened:", page.title())
    print("URL:", page.url)
    print("\nVisible form questions:")

    questions = page.locator('[role="listitem"]')
    for i in range(questions.count()):
        question = questions.nth(i)
        text = question.inner_text().strip()
        if text:
            print(f"\n{i + 1}. {text[:500]}")

    print("\nBrowser open rahega. Form ko manually inspect karo.")
    input("Test complete hone par yahan Enter dabao...")
    browser.close()
