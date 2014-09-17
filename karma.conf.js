module.exports = function(config){
  config.set({
    basePath : './',

    //TODO: add libraries
    //'web/app/components/**/*.js',
    //'web/app/view*/**/*.js'

    files : [
      'web/app/libs/angular/angular.js',
      'web/app/libs/angular-mocks/angular-mocks.js',
      'web/app/main.js'
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