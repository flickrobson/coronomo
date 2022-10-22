import pyotp
import time



#server side
#creates base32 secret that's shared between
#the server and the client
#uses the google authenticator opernSource OTP model
#produces a URI for an exchange of the secret and
#the additional client-server details

def serverSide(email):

    base32secret = pyotp.random_base32()
    print('Secret:', base32secret)


    totp_uri = pyotp.totp.TOTP(base32secret).provisioning_uri(
        email,
        issuer_name="Secure App")
    print(totp_uri)
    #return totp_uri
    return base32secret


def clientSide(server):

    totp = pyotp.TOTP(server)
    print('Your code is:', totp.now())
    return totp.now()



if __name__ == '__main__':
    email = input("Email: ")
    server = serverSide(email)
    client = clientSide(server)
    code = input("What is the code: ")
    print(client == code)

