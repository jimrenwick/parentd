SHELL = /bin/bash
GOOG_PY_CLIENT_HTTP = https://google-api-python-client.googlecode.com/files
GAE_CLIENT = google-api-python-client-gae-1.2.zip

include $(PARENTD_TOOLS)/makefile.lib

build ::
	if [[ ! -d ./apiclient ]]; then \
		wget "$(GOOG_PY_CLIENT_HTTP)/$(GAE_CLIENT)" ; \
		unzip $(GAE_CLIENT) ; \
		rm -f $(GAE_CLIENT) ; \
	fi


distro-clean ::; @rm -rf apiclient httplib2 oauth2client uritemplate

