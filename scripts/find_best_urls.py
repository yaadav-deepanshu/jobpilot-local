import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import urllib.request
import urllib.parse
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9'
}

def test_url(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            code = resp.status
            final_url = resp.geturl()
            # Read first 10k bytes
            content = resp.read(10000).decode('utf-8', errors='ignore').lower()
            if "doesn't seem to exist" in content or "faulty" in content or "page not found" in content:
                return False, code, final_url, "404 text in body"
            if "login.microsoftonline.com" in final_url:
                return False, code, final_url, "SAML login"
            return True, code, final_url, "OK"
    except Exception as e:
        return False, 0, url, str(e)

# Candidate URLs for each company to find the working one
candidates = {
    "amazon_aws": [
        "https://www.amazon.jobs/en/search?base_query=DevOps&loc_query=India",
        "https://www.amazon.jobs/en/search?base_query=Cloud",
        "https://www.amazon.jobs/en"
    ],
    "google": [
        "https://www.google.com/about/careers/applications/jobs/results/?q=DevOps",
        "https://careers.google.com/jobs/results/?q=Cloud",
        "https://careers.google.com"
    ],
    "microsoft": [
        "https://jobs.careers.microsoft.com/global/en/search?q=DevOps&lc=India",
        "https://careers.microsoft.com/professionals/us/en/search-results?keywords=Cloud",
        "https://careers.microsoft.com"
    ],
    "meta": [
        "https://www.metacareers.com/jobs?q=Production+Engineer",
        "https://www.metacareers.com/jobs",
        "https://www.metacareers.com"
    ],
    "apple": [
        "https://jobs.apple.com/en-in/search?search=Cloud&location=india-INDC",
        "https://jobs.apple.com/en-in/search?search=DevOps",
        "https://jobs.apple.com/en-in/search"
    ],
    "oracle": [
        "https://careers.oracle.com/en/sites/jobsearch#en/sites/jobsearch/requisitions?keyword=Cloud",
        "https://careers.oracle.com"
    ],
    "cisco": [
        "https://careers.cisco.com/global/en/search-results?keywords=Cloud%20DevOps",
        "https://careers.cisco.com/global/en"
    ],
    "ibm": [
        "https://www.ibm.com/careers/search?q=DevOps&location=India",
        "https://www.ibm.com/careers"
    ],
    "splunk": [
        "https://careers.cisco.com/global/en/splunk",
        "https://careers.cisco.com/global/en/search-results?keywords=Splunk"
    ],
    "arista": [
        "https://www.arista.com/en/company/careers/open-positions",
        "https://www.arista.com/en/company/careers"
    ],
    "juniper": [
        "https://careers.hpe.com/juniper",
        "https://careers.hpe.com"
    ],
    "nokia": [
        "https://careers.nokia.com/jobs",
        "https://careers.nokia.com"
    ],
    "hp": [
        "https://jobs.hp.com/en-us/search-jobs",
        "https://jobs.hp.com"
    ],
    "dell": [
        "https://jobs.dell.com/search-jobs/Cloud/India",
        "https://jobs.dell.com/search-jobs",
        "https://jobs.dell.com"
    ],
    "westerndigital": [
        "https://careers.smartrecruiters.com/WesternDigital",
        "https://www.westerndigital.com/company/careers"
    ],
    "ti": [
        "https://careers.ti.com/search-jobs",
        "https://careers.ti.com"
    ],
    "qualcomm": [
        "https://careers.qualcomm.com/careers",
        "https://www.qualcomm.com/company/careers"
    ],
    "amd": [
        "https://careers.amd.com/careers-home/jobs?keywords=Cloud",
        "https://careers.amd.com"
    ],
    "intel": [
        "https://jobs.intel.com/en/search-jobs",
        "https://jobs.intel.com"
    ],
    "kpmg": [
        "https://kpmg.com/in/en/home/careers.html",
        "https://kpmg.com/careers"
    ],
    "dxc": [
        "https://careers.dxc.com",
        "https://dxc.wd1.myworkdayjobs.com/en-US/DXC_Jobs"
    ],
    "rackspace": [
        "https://rackspace.wd1.myworkdayjobs.com/en-US/External",
        "https://www.rackspace.com/about/careers"
    ],
    "slalom": [
        "https://www.slalom.com/en/careers",
        "https://www.slalom.com/careers"
    ],
    "techmahindra": [
        "https://careers.techmahindra.com",
        "https://www.techmahindra.com/en-in/careers"
    ],
    "hcl": [
        "https://www.hcltech.com/careers/Careers-in-india",
        "https://www.hcltech.com/careers"
    ],
    "ltimindtree": [
        "https://careers.ltimindtree.com",
        "https://www.ltimindtree.com/careers"
    ],
    "capgemini": [
        "https://www.capgemini.com/in-en/careers/job-search",
        "https://www.capgemini.com/careers"
    ],
    "cognizant": [
        "https://careers.cognizant.com/global/en",
        "https://careers.cognizant.com"
    ],
    "wipro": [
        "https://careers.wipro.com/careers-home",
        "https://careers.wipro.com"
    ],
    "infosys": [
        "https://career.infosys.com",
        "https://www.infosys.com/careers.html"
    ],
    "tcs": [
        "https://www.tcs.com/careers/india",
        "https://www.tcs.com/careers"
    ],
    "accenture": [
        "https://www.accenture.com/in-en/careers/jobsearch",
        "https://www.accenture.com/in-en/careers"
    ],
    "delhivery": [
        "https://www.delhivery.com/careers",
        "https://delhivery.applytojob.com"
    ],
    "nykaa": [
        "https://www.nykaa.com/careers",
        "https://nykaa.darwinbox.in"
    ],
    "makemytrip": [
        "https://careers.makemytrip.com",
        "https://www.makemytrip.com/careers"
    ],
    "ola": [
        "https://www.olaelectric.com/careers",
        "https://olaelectric.darwinbox.in"
    ],
    "postman": [
        "https://www.postman.com/company/careers",
        "https://www.postman.com/careers"
    ],
    "browserstack": [
        "https://www.browserstack.com/careers",
        "https://browserstack.recruitee.com"
    ],
    "freshworks": [
        "https://careers.freshworks.com",
        "https://www.freshworks.com/company/careers"
    ],
    "zepto": [
        "https://www.zepto.com/careers",
        "https://zepto.keka.com"
    ],
    "netflix": [
        "https://jobs.netflix.com/search?q=Cloud",
        "https://jobs.netflix.com"
    ],
    "uber": [
        "https://www.uber.com/global/en/careers/list/?keywords=DevOps",
        "https://www.uber.com/careers"
    ],
    "razorpay": [
        "https://razorpay.com/jobs",
        "https://jobs.lever.co/razorpay"
    ],
    "phonepe": [
        "https://www.phonepe.com/careers",
        "https://phonepe.darwinbox.in"
    ],
    "zomato": [
        "https://www.zomato.com/careers",
        "https://zomato.darwinbox.in"
    ],
    "flipkart": [
        "https://www.flipkartcareers.com/#!/searchjobs",
        "https://www.flipkartcareers.com"
    ],
    "swiggy": [
        "https://careers.swiggy.in/#/jobs",
        "https://careers.swiggy.in"
    ],
    "bnymellon": [
        "https://jobs.bnymellon.com",
        "https://www.bny.com/corporate/global/en/about-us/careers.html"
    ],
    "capitalone": [
        "https://www.capitalonecareers.com",
        "https://www.capitalone.com/careers"
    ],
    "paypal": [
        "https://paypal.wd1.myworkdayjobs.com/en-US/paypal-jobs",
        "https://careers.pypl.com"
    ],
    "blackrock": [
        "https://careers.blackrock.com",
        "https://www.blackrock.com/corporate/careers"
    ],
    "standardchartered": [
        "https://jobs.standardchartered.com",
        "https://www.sc.com/en/careers"
    ],
    "hsbc": [
        "https://mycareer.hsbc.com/en_GB/external",
        "https://www.hsbc.com/careers"
    ],
    "db": [
        "https://careers.db.com/professionals/search-roles",
        "https://careers.db.com"
    ],
    "citi": [
        "https://jobs.citi.com/search-jobs",
        "https://jobs.citi.com"
    ],
    "fidelity": [
        "https://jobs.fidelity.com/search-jobs",
        "https://jobs.fidelity.com"
    ],
    "amex": [
        "https://aexp.eightfold.ai/careers",
        "https://careers.americanexpress.com"
    ],
    "wellsfargo": [
        "https://www.wellsfargojobs.com/en/jobs",
        "https://www.wellsfargojobs.com"
    ],
    "barclays": [
        "https://search.jobs.barclays/search-jobs",
        "https://search.jobs.barclays"
    ],
    "morganstanley": [
        "https://morganstanley.tal.net/vx/lang-en-GB/candidate/jobboard/vacancy/1/adv/",
        "https://www.morganstanley.com/people-opportunities/careers"
    ],
    "goldmansachs": [
        "https://www.goldmansachs.com/careers/search-jobs",
        "https://www.goldmansachs.com/careers"
    ],
    "jpmorgan": [
        "https://careers.jpmorgan.com/global/en/job-search",
        "https://careers.jpmorgan.com"
    ],
    "box": [
        "https://careers.box.com",
        "https://www.box.com/careers"
    ],
    "slack": [
        "https://slack.com/careers",
        "https://salesforce.wd1.myworkdayjobs.com/External_Career_Site"
    ],
    "zoom": [
        "https://www.careers.zoom.us",
        "https://careers.zoom.us"
    ],
    "paloaltonetworks": [
        "https://jobs.paloaltonetworks.com/en/jobs",
        "https://jobs.paloaltonetworks.com"
    ],
    "snowflake": [
        "https://careers.snowflake.com/us/en/search-results",
        "https://careers.snowflake.com"
    ],
    "sap": [
        "https://jobs.sap.com/search",
        "https://jobs.sap.com"
    ],
    "intuit": [
        "https://jobs.intuit.com/search-jobs",
        "https://jobs.intuit.com"
    ],
    "atlassian": [
        "https://www.atlassian.com/company/careers/all-jobs",
        "https://www.atlassian.com/company/careers"
    ],
    "salesforce": [
        "https://salesforce.wd1.myworkdayjobs.com/External_Career_Site",
        "https://careers.salesforce.com"
    ],
    "netapp": [
        "https://careers.netapp.com/search",
        "https://careers.netapp.com"
    ],
    "akamai": [
        "https://www.akamai.com/careers",
        "https://akamai.wd1.myworkdayjobs.com/en-US/Akamai_Careers"
    ],
    "digitalocean": [
        "https://www.digitalocean.com/careers",
        "https://boards.greenhouse.io/digitalocean"
    ]
}

print(f"Testing {len(candidates)} companies...")
best_urls = {}
failed_comps = []

for cid, urls in candidates.items():
    found = False
    for u in urls:
        ok, code, fin, msg = test_url(u)
        if ok and 200 <= code < 400:
            best_urls[cid] = fin
            print(f"✓ [{cid}]: {fin} (HTTP {code})")
            found = True
            break
    if not found:
        failed_comps.append(cid)
        print(f"✗ [{cid}]: Failed all candidate URLs")

print(f"\nSummary: {len(best_urls)} verified working, {len(failed_comps)} failed")
