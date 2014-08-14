#from bottle import run as run_bottle, request#, get, route #, post, delete
import bottle

def get(route):
  def decorator(f):
    f.get = route
    return f
  return decorator

def delete(route):
  def decorator(f):
    f.delete = route
    return f
  return decorator

class Server():
  def __init__(self, repo):
    self.repo = repo
    self.run = bottle.run

  @get('/clusters/')
  def get_clusters(self):
    page = int(bottle.request.query.page or '1')
    page_size = int(bottle.request.query.page_size or '50')

    clusters = self.repo.find_clusters(page, page_size)

    return {
      '_links': {
        'self': {'href':'/?page={}'.format(page)},
        # TODO: show prev
        'next': {'href':'/?page={}'.format(page + 1)}  # TODO: only show next if there are more elements
      },
      '_embedded': {
        'clusters' : [
          {
            '_links': {'self': {'href':'/{}/{}'.format(hash, size)} },
            'hash':hash, 
            'size':size, 
            'count':count
          }
          for hash,size,count 
          in clusters
        ]
      }
    }

  @get('/clusters/<hash>/<size>')
  def get_cluster(self, hash, size):
    return {
      'hash': hash,
      'size': size,
      '_embedded': {
        'files': [
          {
            '_links': {
              'self': {'href': '/files/{}'.format(path)},
              'thumb': {'href': '/static/{}/thumb'.format(path)},
              'download': {'href': '/static/{}'.format(path)}
            },
            'fullname': fullname,
            'size': file_size,
            'hash': file_hash,
            'path': path,
            'abspath': abspath,
            'realpath': realpath
          }
          for fullname, file_size, file_hash, path, abspath, realpath
          in self.repo.findBy_hash_size(hash, size)
        ]
      }
    }

  @get('/files/<abspath:path>')
  def get_file(self, abspath):
    print abspath

  @delete('/files/<abspath:path>')
  def delete_file(self, abspath):
    try:
      self.repo.delete_file(abspath)
    except Exception as e:
      print "EEEE: ", str(e)
      bottle.response.status = str(e)

def routeapp(server):
  # print dir(server)
  for kw in dir(server):
    # print "kw: ", kw
    attr = getattr(server, kw)
    if hasattr(attr, 'get'):
      print "- attr: ", attr
      print "- attr.get: ", attr.get
      # traceback.print_exc()
      bottle.get(attr.get)(attr)
    if hasattr(attr, 'delete'):
      print "- attr: ", attr
      print "- attr.delete: ", attr.delete
      # traceback.print_exc()
      bottle.delete(attr.delete)(attr)

def create_server(repo):
  server = Server(repo)
  routeapp(server)

  return server