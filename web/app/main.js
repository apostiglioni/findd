var app = angular.module('dupfind', ['ui.bootstrap', 'ui.checkbox', 'ngResource'])

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

  $scope.toggleFileSelection = function(cluster, file, $event) {
    $log.debug('file.selected: ' + file.selected)
    return false
  }


  $scope.selectOthers = function(cluster, file) {
    var files = getFiles(cluster)
    angular.forEach(files, function(f, idx) {
      f.selected = f != file
    })
  }

  $scope.validateFileSelected = function(cluster, file) {
    //We're trying to unselect, which is always allowed
    if (file.selected) {
        return true
    }

    //If there's more than one unselected, then it's safe to select
    var unselectedCount = 0
    var files = getFiles(cluster)
    for(i=0; i<files.length; i++) {
      if (!files[i].selected) {
        unselectedCount++
      }
      if (unselectedCount > 1) {
        return true
      }
    }

    //There's no more than one unselected, so we can't select
    return false
  }

  $scope.getFiles = getFiles

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

  $scope.deleteFromCluster = function(cluster) {
    var Files = $resource('/webapp/filesss/:abspath')

    angular.forEach(getFiles(cluster), function(file, idx) {
      if (file.selected) {
        Files.delete({
          abspath: file.abspath
        }, function(hal) {
          console.log(hal)
        })
      }
    });
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
          return getFiles(cluster);
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

/********************************* private functions ********************************/
  function getFiles(cluster) {
    return cluster['_embedded']['files']
  }
/********************************* private functions ********************************/



app.directive('dupCheckbox', function () {
  return {
    require: ['dupCheckbox', 'ngModel'],
    controller: 'ButtonsController',
    link: function (scope, element, attrs, ctrls) {
      var buttonsCtrl = ctrls[0], ngModelCtrl = ctrls[1];

      function getTrueValue() {
        return getCheckboxValue(attrs.btnCheckboxTrue, true);
      }

      function getFalseValue() {
        return getCheckboxValue(attrs.btnCheckboxFalse, false);
      }

      function getCheckboxValue(attributeValue, defaultValue) {
        var val = scope.$eval(attributeValue);
        return angular.isDefined(val) ? val : defaultValue;
      }

      function validate() {
        return !angular.isDefined(attrs.dupCheckboxValidate) || scope.$eval(attrs.dupCheckboxValidate);
      }

      //model -> UI
      ngModelCtrl.$render = function () {
        element.toggleClass(buttonsCtrl.activeClass, angular.equals(ngModelCtrl.$modelValue, getTrueValue()));
      };

      //ui->model
      element.bind(buttonsCtrl.toggleEvent, function () {
        if (validate()) {
          scope.$apply(function () {
            ngModelCtrl.$setViewValue(element.hasClass(buttonsCtrl.activeClass) ? getFalseValue() : getTrueValue());
            ngModelCtrl.$render();
          });
        }
      });
    }
  };
});
