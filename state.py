import threading

class ClientStateManager: 

  def __init__(self):
    self.recent_game_matches = []
    self.thread = None

  def store_game_matches(self, game_matches): 
    self.recent_game_matches = game_matches
    two_minutes = 2 * 60
    if self.thread != None: 
      self.thread.cancel()
    self.thread = threading.Timer(interval=two_minutes, function= self.clear_game_matches)
    self.thread.start()
    print("clear matches in two minutes - thread started")

  def get_game_matches(self):
    return self.recent_game_matches

  def clear_game_matches(self): 
    print("clearing matches")
    self.recent_game_matches = []
    self.thread.cancel()
    self.thread = None