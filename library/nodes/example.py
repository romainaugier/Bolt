import bolt
import typing


class ExampleNode(bolt.Node):
    
    def __init__(self) -> None:
        super().__init__()
        
        self.add_input()

        self.add_parameter()

        self.add_output()
    
    def cook(self) -> bolt.CookResult:
        print("Hello from example node")