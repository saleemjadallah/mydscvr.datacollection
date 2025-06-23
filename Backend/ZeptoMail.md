import requests

url = "https://api.zeptomail.com/v1.1/email"

payload = "{\n\"from\": { \"address\": \"noreply@mydscvr.ai\"},\n\"to\": [{\"email_address\": {\"address\": \"support@mydscvr.ai\",\"name\": \"Saleem\"}}],\n\"subject\":\"Test Email\",\n\"htmlbody\":\"<div><b> Test email sent successfully.  </b></div>\"\n}"
headers = {
'accept': "application/json",
'content-type': "application/json",
'authorization': "Zoho-enczapikey wSsVR61y+BWmWqkrmT2qLus4mVsDAl71FE9+3lKm6CT0HP3Ap8c8kRGdA1LzFfFJQjM7QWBDp7osmxsG0zpb2457yF4CXiiF9mqRe1U4J3x17qnvhDzPXWpelxuMK4gJwA5pmGJkG8sk+g==",
}

response = requests.request("POST", url, data=payload, headers=headers)

print(response.text)