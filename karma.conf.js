module.exports = function(config){
  config.set({
    basePath : './',

    //TODO: add libraries
    //'web/app/components/**/*.js',
    //'web/app/view*/**/*.js'

    files : [
      'web/app/libs/angular/angular.js',
      'web/app/libs/angular-resource/angular-resource.js',
      'web/app/libs/angular-bootstrap/ui-bootstrap-tpls.min.js',
      'web/app/main.js',

      'web/app/libs/angular-mocks/angular-mocks.js',
      'web/app/libs/jquery/dist/jquery.js',
      'web/app/libs/jasmine-jquery/lib/jasmine-jquery.js',
      'test/web/main.spec.js',
      {pattern: 'test/web/*.fixture.json', watched: true, served: true, included: false}
    ],

    autoWatch : true,

    frameworks: ['jasmine'],

    browsers : ['Chrome'],

    plugins : [
            'karma-chrome-launcher',
            'karma-firefox-launcher',
            'karma-jasmine',
            'karma-junit-reporter'
            ],

    junitReporter : {
      outputFile: 'test_out/unit.xml',
      suite: 'unit'
    }

  });
};