import pyotp
import time
import re



#server side
#creates base32 secret that's shared between
#the server and the client
#uses the google authenticator opernSource OTP model
#produces a URI for an exchange of the secret and
#the additional client-server details

def serverSide(email):

    base32secret = pyotp.random_base32()
    totp_uri = pyotp.totp.TOTP(base32secret).provisioning_uri(
        email, issuer_name="Coronomo")
    print(totp_uri)
    return totp_uri
    #returns similar to this: otpauth://totp/Secure%20App:email@gmail.com?secret=4XR3LTZQJTFF4VWJTI35KSBI75UEYDIK&issuer=Coronomo



def clientSide():

    email = input("Email: ")

    #generates URI from serverSide
    uri = serverSide(email)
    base32 = re.search('=(.*)&', uri)

    #creates the code
    totp = pyotp.TOTP(base32.group(1))
    print('Your code is:', totp.now())

    #checks whether the user enters the correct details in following method
    authentic = check(totp.now(), email)

    return authentic




def check(totp, check_email): #server side?
    #checks details from user
    code = input("What is the code: ")
    email = input("Confirm email: ")

    #checks if they match and returns to client side method
    if  check_email == email:
        return totp == code


if __name__ == '__main__':
    print(clientSide())


