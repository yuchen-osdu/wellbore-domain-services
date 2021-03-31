import os;
import boto3;
import jwt;

def get_id_token():
    client = boto3.client('cognito-idp', region_name=os.environ["AWS_REGION"])
    userAuth = client.initiate_auth(
        ClientId= os.environ['AWS_COGNITO_CLIENT_ID'],
        AuthFlow= os.environ['AWS_COGNITO_AUTH_FLOW'],
        AuthParameters= {
            "USERNAME": os.environ['AWS_COGNITO_AUTH_PARAMS_USER'],
            "PASSWORD": os.environ['AWS_COGNITO_AUTH_PARAMS_PASSWORD']
        })

    print(userAuth['AuthenticationResult']['AccessToken'])


def get_invalid_token():
    #generate a dummy jwt
    return jwt.encode({'some': 'payload'}, 'secret', algorithm='HS256').decode("utf-8")

if __name__ == '__main__':
    get_id_token()
