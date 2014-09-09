angular.module('dupfind', ['ui.bootstrap', 'ui.checkbox', 'ngResource']);

function AccordionDemoCtrl($scope, $resource, $modal, $log) {
  $scope.oneAtATime = true;

  $scope.getElements = function() {
    //var Duplicates = $resource('/clusters/duplicates')
    var Duplicates = $resource('/webapp/duplicates-many.json')
    Duplicates.get({
      page: 1,
      page_size: 100
    }, function(hal) {
      var clusters = hal._embedded.clusters
      $scope.clusters = clusters
    })
  }

  $scope.toggleFileSelection = function(cluster, file) {
    $log.debug('file.selected: ' + file.selected)
  }

  $scope.getFiles = function(cluster) {
    return cluster['_embedded']['files']
  }

  $scope.getThumb = function(file) {
    return file['_links']['thumb']['href']
  }

  $scope.addElement = function() {
    $scope.groups.push({
      title: 'New element',
      content: 'New content'
    });
  }

  $scope.removeElement = function() {
    $scope.groups.pop()
  }

  $scope.addItem = function() {
    var newItemNo = $scope.items.length + 1;
    $scope.items.push('Item ' + newItemNo);
  };

  $scope.status = {
    isFirstOpen: true,
    isFirstDisabled: false
  };

  $scope.deleteFile = function(cluster, file, index) {
    var files = cluster['_embedded']['files'];
    if (files.length > 2) {
      files.splice(index, 1);
    } else {
      clusterIndex = $scope.clusters.indexOf(cluster);
      $scope.clusters.splice(clusterIndex, 1);
    }
  }


  $scope.selectAll = function(cluster) {
    var selected = 0;
    var files = cluster['_embedded']['files'];
    unselected = []
    angular.forEach(files, function(file, index) {
       if(file.selected) {
         selected++
       } else {
         unselected.push(file)
       }
    });

    if (selected < files.length - 1) {
      angular.forEach(unselected, function(file, index) {
        //leave at least one element unselected
        if (index > 1) {
          file.selected = true
        }
      });
    }
  }

  $scope.open = function(cluster) {
    var modalInstance = $modal.open({
      templateUrl: 'myModalContent.html',
      controller: ModalInstanceCtrl,
      //size: 'lg',
      resolve: {
        files: function() {
          return $scope.getFiles(cluster);
        }
      }
    });

    modalInstance.result.then(function(selectedItem) {
      $scope.selected = selectedItem;
    }, function() {
      $log.info('Modal dismissed at: ' + new Date());
    });
  };
};

// Please note that $modalInstance represents a modal window (instance) dependency.
// It is not the same as the $modal service used above.

var ModalInstanceCtrl = function($scope, $modalInstance, files) {

  $scope.getThumb = function(file) {
    return file['_links']['thumb']['href']
  }
  $scope.files = files;
  //$scope.items = items;
  //$scope.selected = {
  //  item: $scope.items[0]
  //};

  $scope.ok = function() {
    //$modalInstance.close($scope.selected.item);
    $modalInstance.close()
  };

  $scope.cancel = function() {
    $modalInstance.dismiss('cancel');
  };
};