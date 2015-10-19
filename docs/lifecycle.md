The application lifecycle for a micro app
------------------------------------------


1 - INIT 
  App instance is created
    1 - default configuration is loaded
    2 - shutdown hook is registered
2 - REGISTER 
  provided modules are instantiated and registered with the app
3 - RUN 
  app run is started
    1 - provided configuration is read an overlaid on the default
    2 - the registry and router are registered and ran
    3 - provided modules are ran
    4 - event loop enters run_forever
4 - STOP 
  loop closes with exit signal or by calling app.stop('SIGTERM')
    1 - all modules stop methods are called
    2 - any remaining events are cancelled
    3 - the event loop is stopped