describe('Unit: ClustersController', function() {
/*  var scope;
  var mockHttpBackend;
  var ClustersController;
   // Load the module with ClustersController
*/   
  // define the mock Duplicates service
  //beforeEach(function($resource) {
  //  DuplicatesMock = $resource('/webapp/duplicates-many.json')
  //})

  var $httpBackend, $rootScope, $scope, createController


/*
  beforeEach(inject(function($rootScope, $controller, $httpBackend) {
    mockHttpBackend = $httpBackend

    scope = $rootScope.$new()
    ClustersController = $controller('ClustersController', {
      $scope: scope
    })
  }))
*/


  beforeEach(module('dupfind'))
  beforeEach(inject(function($injector) {
    jasmine.getJSONFixtures().fixturesPath='base/test/web'

    // Set up the mock http service responses
    $httpBackend = $injector.get('$httpBackend');
    // Get hold of a scope (i.e. the root scope)
    $rootScope = $injector.get('$rootScope');
    //create local scope
    $scope = $rootScope.$new

    // The $controller service is used to create instances of controllers
    var $controller = $injector.get('$controller');

    createController = function() {
      return $controller('ClustersController', {'$scope' : $scope });
    };
  }));

  afterEach(function() {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  it('should only delete the files marked as selected', function () {
    $httpBackend.expectGET('/clusters/duplicates?page=1&page_size=50').respond(200, getJSONFixture('duplicates.fixture.json'))
    
    var controller = createController()
    $scope.loadClusters()
    $httpBackend.flush()
    
    expect($scope.clusters.length).toBeGreaterThan(0)

    $scope.clusters.forEach(function(cluster) {
      cluster.files.forEach(function(file) {
        if (file.selected) {
          $httpBackend.expectDELETE(file.self)
        }
      })
    })
  });
})