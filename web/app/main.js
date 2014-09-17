var app = angular.module('dupfind', ['ui.bootstrap', 'ngResource'])

app.controller('AlertsController', function($scope, notifications) {
  $scope.alerts = notifications.queue
  console.log(notifications.queue)
})

app.factory('Duplicates', function($resource) {
  return $resource('/clusters/duplicates')
})

app.factory('Files', function($resource) {
  return $resource('/webapp/files/:abspath')
})

app.controller('ClustersController', function($scope, Duplicates, Files, $modal, $log, notifications) {
  $scope.oneAtATime = true;

  $scope.getElements = function(page) {
    const PAGE_SIZE = 1
    Duplicates.get({
      page: page,
      page_size: PAGE_SIZE
    }, function(hal) {
      //TODO: Wrap the payload details into the service
      var clusters = hal._embedded.clusters
      $scope.clusters = clusters
    })
  }

  $scope.clearSelection = function(cluster) {
    angular.forEach(getFiles(cluster), function(file, idx) {
      file.selected = false
    })
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
  $scope.getThumb = getThumb

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

  $scope.openConfirmationDialog = function(cluster) {
    var toDelete = []
      angular.forEach(getFiles(cluster), function(file, idx) {
      if (file.selected) {
        toDelete.push(file)
      }
    })
    if (toDelete.length < 1) return

    var modalInstance = $modal.open({
      templateUrl: 'confirmDeleteDialog.html',
      controller: ConfirmDeleteDialogController,
      resolve: {
        filesToDelete: function() {
          return toDelete;
        }
      }
    });

    modalInstance.result.then(
      function(result) {
        if ('delete' != result) return

        deleteFromCluster(cluster)
      },
      function() {
        $log.info('Modal dismissed at: ' + new Date());
      }
    );
  }

  $scope.selectAll = function(cluster) {
    var selected = 0;
    var files = getFiles(cluster);
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
      templateUrl: 'preview.html',
      controller: PreviewModalController,
      //size: 'lg',
      resolve: {
        files: function() {
          return getFiles(cluster);
        }
      }
    });

    modalInstance.result.then(
      function(selectedItem) {
        $scope.selected = selectedItem;
      },
      function() {
          $log.info('Modal dismissed at: ' + new Date());
      });
  };
});

// Please note that $modalInstance represents a modal window (instance) dependency.
// It is not the same as the $modal service used above.
var PreviewModalController = function($scope, $modalInstance, files) {
  $scope.getThumb = getThumb

  $scope.files = files;

  $scope.ok = function() {
    //$modalInstance.close($scope.selected.item);
    $modalInstance.close()
  };

  $scope.cancel = function() {
    $modalInstance.dismiss('cancel');
  };
};


var ConfirmDeleteDialogController = function($scope, $modalInstance, filesToDelete) {
  $scope.filesToDelete = filesToDelete

  $scope.confirm = function() {
    $modalInstance.close('delete')
  }

  $scope.cancel = function() {
    $modalInstance.dismiss('cancel')
  }
}





/********************************* private functions ********************************/
  function getFiles(cluster) {
    return cluster['_embedded']['files']
  }

  function getThumb(file) {
    return file['_links']['thumb']['href']
  }

  function deleteFromCluster(cluster) {
    var toDelete = getFiles(cluster).slice(0)
    angular.forEach(toDelete, function(file, idx) {
      if (file.selected) {
        Files.delete({
          abspath: file.abspath
        }, 
        function(hal) {
          var filesInCluster = getFiles(cluster)
          var idx = filesInCluster.indexOf(file)
          if (idx >=0) {
            filesInCluster.splice(idx, 1)
          }
          else {
            notifications.warning('Not found in files array:  '+file.abspath, 3000)
          }
        }, 
        function(err) {
          notifications.danger('Server error deleting '+file.abspath, 3000)
        })
      }
    });

  }
/********************************* private functions ********************************/

app.factory('notifications', function($timeout) {
  var queue = []
  var add = function(msg, type, timeout) {
    var item = {type: type, message: msg}
    queue.push(item)
    if (timeout) {
      $timeout(function() {
        var idx = queue.indexOf(item)
        if (idx >= 0) {
            queue.splice(idx, 1)
        }
      }, timeout)
    }
  }

  var notifications = {
    queue: queue,
    add: add,
    danger: function(msg, timeout) { add(msg, 'danger', timeout) },
    success: function(msg, timeout) { add(msg, 'success', timeout) },
    warning: function(msg, timeout) { add(msg, 'warning', timeout) },
    info: function(msg, timeout) { add(msg, 'info', timeout) }
  }
  return notifications
})

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




















/**
  <body ng-controller="MainCtrl">
     <script type="text/ng-template" id="templateId.html">
       <img src='http://db3.stb.s-msn.com/i/20/1FDB35FC17BD886FAC93E2E2FA6FDC.jpg' class="img-responsive">
      This is the content of the template
    </script>
     <a href="#" mypopover   title="title">Click here</a>
  </body>
**/




app.directive('mypopover', function ($compile,$templateCache) {

var getTemplate = function (contentType) {
    var template = '';
    switch (contentType) {
        case 'user':
            template = $templateCache.get("templateId.html");
            break;
    }
    return template;
}
return {
    restrict: "A",
    link: function (scope, element, attrs) {
        var popOverContent;

        popOverContent = getTemplate("user");

        var options = {
            content: popOverContent,
            placement: "bottom",
            html: true,
            date: scope.date
        };
        $(element).popover(options);
    }
};
});