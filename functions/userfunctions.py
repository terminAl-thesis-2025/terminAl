import sys

class UserFunctions:
    pass

    @classmethod
    def check_user_input(cls, user_input):
        if user_input.startswith(r"\exit"):
            cls.exit()
        elif user_input.startswith("\\help"):
            #TODO print help statements
            pass

    @classmethod
    def exit(cls):
        print("Exiting application...")
        sys.exit(0)



