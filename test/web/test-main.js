describe('Unit: ClustersController', function() {
  var scope;
  var DuplicatesMock;
  var ClustersController;
   // Load the module with ClustersController
  beforeEach(module('dupfind'));
  // define the mock Duplicates service
  //beforeEach(function($resource) {
  //  DuplicatesMock = $resource('/webapp/duplicates-many.json')
  //})
  beforeEach(inject(function($rootScope, $controller, $resource) {
    DuplicatesMock = $resource('/webapp/duplicates-many.json')

    scope = $rootScope.$new()
    ClustersController = $controller('ClustersController', {
      $scope: scope, Duplicates: DuplicatesMock
    })
  }))

  it('should only delete the files marked as selected', function () {
    spyOn(DuplicatesMock, 'get').and.callThrough()

    scope.getElements()


  });


})