from ngapp.cli.serve_standalone import main as startup


def main():
    startup(app_module="mapp.appconfig")
    
if __name__ == "__main__":
    main()
