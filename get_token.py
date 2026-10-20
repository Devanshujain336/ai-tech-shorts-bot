from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# prompt='consent' forces Google to issue a fresh, non-empty refresh_token
flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

# Test refreshing right now on your laptop to prove it works
test_creds = Credentials(
    None,
    refresh_token=creds.refresh_token,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=creds.client_id,
    client_secret=creds.client_secret,
    scopes=SCOPES
)
test_creds.refresh(Request())
print("\n✅ TOKEN TEST PASSED! Copy ONLY the text inside the quotes below:\n")

print(f'YT_CLIENT_ID:\n{creds.client_id}\n')
print(f'YT_CLIENT_SECRET:\n{creds.client_secret}\n')
print(f'YT_REFRESH_TOKEN:\n{creds.refresh_token}\n')
