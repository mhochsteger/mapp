from webapp_client.cli.serve_standalone import main as startup


def main():
    startup("mapp.appconfig", False, True)
