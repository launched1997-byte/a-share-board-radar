import akshare as ak


def get_spot():
    return ak.stock_zh_a_spot_em()


def get_limit_up_pool():
    return ak.stock_zt_pool_em()


def get_yesterday_limit_up():
    return ak.stock_zt_pool_previous_em()
