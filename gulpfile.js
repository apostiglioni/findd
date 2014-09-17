var gulp = require('gulp');
var karma = require('gulp-karma');


var bower = require('gulp-bower');

gulp.task('bower', function() {
  return bower()
    .pipe(gulp.dest('web/app/libs/'))
});

gulp.task('default', function() {
  // place code for your default task here
});

var testFiles = [
'web/app/libs/angularjs/**/*.js',
      'web/app/libs/**/*.js',
      'test/libs/angular-mocks-1.2.10.js',
      'web/app/main.js',
  'test/web/*.js'
];

gulp.task('test', function() {
  // Be sure to return the stream
  return gulp.src(testFiles)
    .pipe(karma({
      configFile: 'karma.conf.js',
      action: 'run'
    }))
    .on('error', function(err) {
      // Make sure failed tests cause gulp to exit non-zero
      throw err;
    });
});

gulp.task('watch', function() {
  gulp.src(testFiles)
    .pipe(karma({
      configFile: 'karma.conf.js',
      action: 'watch'
    }));
});