LANGS := $(patsubst obkey.%.po,%,$(wildcard *.po))
TARGETS := $(patsubst %,../locale/%/LC_MESSAGES/obkey.mo,$(LANGS))

all: $(TARGETS)

../locale/%/LC_MESSAGES/obkey.mo: obkey.%.po
	mkdir -p $(dir $@)
	msgfmt -o $@ $<
