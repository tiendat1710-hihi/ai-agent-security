import config
from lab import mail_client, seed_data


def reset():
    mail_client.clear_mailbox(config.INTERNAL_MAIL)
    mail_client.clear_mailbox(config.EXTERNAL_MAIL)
    seed_data.main()


if __name__ == "__main__":
    reset()
    print("Lab da reset: 2 hop thu trong, database sinh lai.")