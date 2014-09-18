var app = angular.module('dupfind', ['ui.bootstrap', 'ngResource'])

app.factory('halParser', function($resource) {
  //private functions
  function parseElement(element) {
      var ret
      if (Array.isArray(element)) {
        ret = element.map(function(e) { return halParser(e, $resource) })
      }
      else {
        ret = halParser(element)
      }

      return ret
  }

  return {
    parse: function(hal) {
      var resource = angular.copy(hal)
      delete resource._embedded
      delete resource._links

      var embedded = hal._embedded || {}
      for (var key in embedded) {
        resource[key] = halElementParser(embedded[key], $resource)
      }

      var links = hal._links || {}
      resource.link = function(name, parameters) {
        return links[name].href //TODO: support parameters for templated links
      }

      //Create nested resource
      if (links.hasOwnProperty('self')) {
        var actions = ['get', 'save', 'query', 'remove', 'delete']
        var $r = $resource(resource.link('self'))
        actions.forEach(function(action) {
          resource['$' + action] = $r[action]
        })
      }

      return resource
    }
  }
})


app.controller('AlertsController', function($scope, notifications) {
  $scope.alerts = notifications.queue
})

app.factory('Clusters', function(halParser, $respource) {
  var resource = $resource(
    '/clusters/:verb', {},
    {
      getDuplicates: {
        method: 'GET', 
        params: {verb: 'duplicates'},
        transformResponse: function(json, headers) {
          var data = angular.fromJson(json)
          //TODO: page could probably be a first class citizen object
          var page = {
            //$rawHalResponse: json  //no need to save the raw json yet
            data: halParser.parse(data).clusters,
            hasNext: data._links.hasOwnProperty('next')
          }

          return page;
        }
      }
    }
  )
  return {
    getDuplicates: function(params) {
      return resource.getDuplicates(params).$promise
    }
  }
})

app.factory('Files', function($resource) {
  return $resource('/webapp/files/:abspath')
})

app.controller('ClustersController', function($scope, Clusters, Files, $modal, $log, notifications) {
  var currentPage = 1  //private variable, not kept in scope
  $scope.oneAtATime = true;
  $scope.clusters = []

  //TODO: Wrap this into its own controller
  $scope.loadClusters = function() {
    const PAGE_SIZE = 50

    Clusters.getDuplicates({
      page: currentPage++,
      page_size: PAGE_SIZE
    }).then(function(page) {
      $scope.clusters = $scope.clusters.concat(page.data)
      $scope.hasMorePages = page.hasNext
    })
  }

  $scope.clearSelection = function(cluster) {
    angular.forEach(cluster.files, function(file, idx) {
      file.selected = false
    })
  }

  $scope.selectOthers = function(cluster, file) {
    angular.forEach(cluster.files, function(f, idx) {
      f.selected = f != file
    })
  }

  $scope.validateFileSelected = function(cluster, file) {
    //We're trying to unselect, which is always allowed
    if (file.selected) {
        return true
    }

    //If there's more than one unselected, then it's safe to select
    //TODO: This could probably be done using Array.prototype.every
    var unselectedCount = 0
    var files = cluster.files
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

  $scope.getThumb = getThumb

  $scope.openConfirmationDialog = function(cluster) {
    //TODO: implement this with Array.prototype.filter
    var toDelete = []
      angular.forEach(cluster.files, function(file, idx) {
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
    var files = cluster.files
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


  $scope.preview = function(cluster) {
    var modalInstance = $modal.open({
      templateUrl: 'preview.html',
      controller: PreviewModalController,
      //size: 'lg',
      resolve: {
        files: function() {
          return cluster.files
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
  function getThumb(file) {
    return file.link('thumb')
  }

  function deleteFromCluster(cluster) {
    var toDelete = cluster.files.slice(0)
    angular.forEach(toDelete, function(file, idx) {
      if (file.selected) {
        Files.delete({
          abspath: file.abspath
        }, 
        function(hal) {
          var filesInCluster = cluster.files
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