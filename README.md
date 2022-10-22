# Coronomo


A bluetooth contract tracing system. Users have an app which exchanges keys after a period of time. 
If a user receives a positive covid test, they will receive a call from a health service provider, who will provide the user with a one time code. This one time code is put into the app and sent to the SQL database along with the diagnosis keys to be validated. If the one time code is valid, the diagnosis keys are inserted into the centralised database. 
Every two hours, all Coronomo apps retrieve all the diagnosis keys from the database to determine if they have a match in their own list of contacts. 
If a key from the databases matches one stored in the app, an alert is shown to the user telling them they have been exposed and should be tested.
