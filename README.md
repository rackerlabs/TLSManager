# TLSManager

## About
TLSManager is a tool that uses the [SSL Labs API][ssllabs] to scan SSL/TLS
servers for potential security issues, including:

- certificate expiration
- insecure cipher support
- insecure protocol support
- insecure key lengths
- susceptibility to known vulnerabilities

## Dependencies
- [Virtualenv][venv] (OPTIONAL)

## Setup

#### Clone the repository
```bash
git clone https://github.com/rackerlabs/TLSManager.git
OR
git clone git@github.com:rackerlabs/TLSManager.git
```

#### Set up virtualenv (OPTIONAL)
```bash
virtualenv $VIRTUALENVS_DIRECTORY/TLSM
source $VIRTUALENVS_DIRECTORY/TLSM/bin/activate
```

#### Configure Django settings (settings.py.dist)

- Set the `SESSION_COOKIE_DOMAIN` variable to the appropriate domain name
where the app will be served
- Change the `SECRET_KEY` to a long, random string. Keep this safe! You can
also use an environment variable to be able to change this value more
easily. Be sure not to print this in logs or check it into public source
control!
- (OPTIONAL) If you want to utilize TLSManager's email functionality,
update the `EMAIL_*` variables at the bottom to reflect your SMTP
configuration
- Add any administrators to the `ADMINS` variable
- Finally, rename the `settings.py.dist` file to `settings.py`

#### Install PIP dependencies
```bash
pip install -r requirements.txt
```

#### Run DB setup

The last step will ask you to add a Django superuser (go ahead and do this now).

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py syncdb
```

#### Run the server
```bash
EX: python manage.py runserver localhost:7070
```

#### Kick off the background thread

You'll need to initialize the thread that runs the SSL tests, and you can
do so by visiting the `/init` URL after logging in. This will create a file
in the `PROJECT_DIRECTORY` called 'semaphore.' When you're ready to kill the
server, you'll need to delete this file as well. We will likely change this
in the future.


## License

TLSManager is licensed under the [Apache 2.0 license](http://www.apache.org/licenses/LICENSE-2.0).

[ssllabs]: https://www.ssllabs.com/projects/ssllabs-apis/
[venv]: https://pypi.python.org/pypi/virtualenv
