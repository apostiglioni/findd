#from bottle import run as run_bottle, request, static_file  #, get, route #, post, delete
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

    @get('/clusters/duplicates')
    def get_clusters(self):
        page = int(bottle.request.query.page or '1')
        page_size = int(bottle.request.query.page_size or '50')

        limit = page_size + 1
        offset = page_size * (page-1)
        clusters = self.repo.find_duplicate_clusters(limit, offset).fetchall()
        has_next = len(clusters) > page_size
        if has_next:
          clusters.pop()

        ret = {
            '_links': {
                'self': {'href': '/?page=%d' % page},
                # TODO: show prev
                'prev': { 'href': '/page=%d' % (page - 1) },
                'next': { 'href': '/?page=%d' % (page + 1)}  # TODO: only show next if there are more elements
            },
            '_embedded': {
                'clusters': [
                    {
                        '_links': {'self': {'href': '/{}/{}'.format(hash, size)}},
                        '_embedded': self.get_cluster(hash, size)['_embedded'],
                        'hash': hash,
                        'size': size,
                        'count': count
                    }
                    for hash, size, count
                    in clusters
                ]
            }
        }

        return ret

    @get('/clusters/<hash>/<size>')
    def get_cluster(self, hash, size):
        return {
            'hash': hash,
            'size': size,
            '_embedded': {
                'files': [
                    {
                        '_links': {
                            'self': {'href': '/files/{}'.format(abspath)},
                            'thumb': {'href': '/static/{}'.format(abspath)},
                            'download': {'href': '/static/{}'.format(abspath)}
                        },
                        'fullname': fullname,
                        'size': file_size,
                        'hash': file_hash,
                        'path': path,
                        'abspath': abspath,
                        # 'realpath': realpath
                    }
                    for fullname, file_size, file_hash, path, abspath
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

    @get('/static/<abspath:path>')
    def get_static(self, abspath):
        return bottle.static_file(abspath, root='/')


    @get('/webapp/<abspath:path>')
    def get_static_app(self, abspath):
        import os
        cwd = os.path.dirname(os.path.realpath(__file__))

        return bottle.static_file(abspath, root=os.path.join(cwd, 'app'))


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
