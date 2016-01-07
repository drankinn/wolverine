#!/usr/bin/with-contenv sh

/env/bin/py.test --cov=wolverine --cov-report xml --junitxml=tests.xml
/env/bin/python -m cob_to_clover.clover coverage.xml -o clover.xml