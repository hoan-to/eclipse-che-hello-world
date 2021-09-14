import requests, json, getpass

def main():
    
    token_url = "https://auth.dlr.wobcom.tech/auth/realms/default/protocol/openid-connect/token"
    test_api_url = "https://api.dlr.wobcom.tech/quantumleap/v2/entities/urn:ngsiv2:Ecg:Patient01?limit=10000"

    #Resource owner (enduser) credential
    RO_user = input('Enduser netid: ')
    RO_password = getpass.getpass('Enduser password: ')

    client_id = 'api'

    #step B, C - single call with resource owner credentials in the body  and client credentials as the basic auth header
    # will return access_token

    data = {'grant_type': 'password','username': RO_user, 'password': RO_password, 'scope': 'entity:read entity:write entity:delete entity:op entity:create subscription:read subscription:create subscription:write subscription:delete', 'client_id': 'api'}

    access_token_response = requests.post(token_url,data=data, verify=False, allow_redirects=False)

    tokens = json.loads(access_token_response.text)

    # Step C - now we can use the access_token to make as many calls as we want.
    api_call_headers = {'Authorization': 'Bearer ' + tokens['access_token'], 'fiware-service': 'dlr_ekg', 'fiware-servicepath': '/dlr_ekg'}
    print(api_call_headers)
    api_call_response = requests.get(test_api_url, headers=api_call_headers, verify=False)

    print(api_call_response.text)

if __name__ == '__main__':
    main()