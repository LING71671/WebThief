---
slug: browser
section: Browser
title: Browser
path:
  - Browser
---

# Browser

Antigravity has the ability to open, read, and control a Chrome browser, allowing you to test development websites, read internet data sources, and automate various different browser tasks.

Using a [subagent](/docs/browser-subagent), Antigravity can operate on the browser as it sees fit, as well as [recording its actions](/docs/browser-recordings) and presenting select screenshots and videos as [artifacts](/docs/screenshots).

To isolate the Antigravity agent from your normal browsing, it runs in a separate browser profile. This means that it will show up as a separate application in your dock and nothing will be signed in. You can read more about this in the [Separate Chrome Profile](/docs/separate-chrome-profile) section.

To disable the use of all browser tools, you may disable the browser tools setting in the â€œBrowserâ€ section of your settings.

![Enable Browser Tools](/assets/image/docs/enable_browser_tools.png)

Antigravity detects and uses your existing Chrome application. If you donâ€™t already have Chrome, you must download it here. If Antigravity is unable to detect your chrome installation, you may have to specify the path to it in the following setting:

![Chrome Binary Path](/assets/image/docs/chrome_binary_path.png)
