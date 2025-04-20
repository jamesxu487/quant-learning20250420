import backtrader as bt


class NaiveRsiStrategy(bt.Strategy):
    """
    使用内置 RSI 指标的策略示例：
    - 仅当无持仓且 RSI 低于超卖阈值时，下满仓单；
    - 仅当有持仓且 RSI 高于超买阈值时，清仓；
    - 订单部分成交时取消剩余部分，防止订单一直挂单阻塞新信号；
    - 日志输出中文信息，包含时间戳和订单执行细节。
    """

    params = (
        ("period", 14),         # RSI 计算周期
        ("overbought", 70),     # 超买阈值
        ("oversold", 30),       # 超卖阈值
    )

    def log(self, txt, dt=None):
        """统一的日志输出函数，使用中文并打印具体时间。"""
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f"{dt.strftime('%Y-%m-%d %H:%M:%S')}  {txt}")

    def __init__(self):
        self.dataclose = self.datas[0].close
        # 使用 Backtrader 内置的 RSI 指标，仅基于最近 period 个周期的数据
        self.rsi = bt.indicators.RSI(self.data, period=self.params.period)
        self.order = None  # 用于跟踪当前活跃订单，避免重复下单

    def notify_order(self, order):
        """
        订单状态改变时调用：
        - 在订单提交/接收时打印日志；
        - 对于部分成交的订单，主动取消剩余部分，避免长时间挂单阻塞新交易信号；
        - 在订单完全成交或取消/拒绝时，重置 self.order。
        """
        if order.status in [order.Submitted, order.Accepted]:
            self.log(f"订单状态: {order.getstatusname()} (提交/接收)，等待成交...")
            return

        if order.status == order.Partial:
            self.log(f"订单部分成交: 剩余数量={order.created.size - order.executed.size}，已成交数量={order.executed.size}")
            # 主动取消未成交部分，确保不会阻塞后续下单
            self.cancel(order)
            return

        if order.status == order.Completed:
            if order.isbuy():
                self.log(f"买单执行: 买入成交量={order.executed.size}, 买入成交价={order.executed.price:.2f}, "
                         f"订单金额={order.executed.value:.2f}, 手续费={order.executed.comm:.2f}")
            elif order.issell():
              #  self.log(f"卖单执行: 成交量={order.executed.size}, 成交价={order.executed.price:.2f}, "
              #           f"订单金额={order.executed.value:.2f}, 手续费={order.executed.comm:.2f}")
                # 卖出时候的框架金额计算，等于卖出量 * 买入价，正常应该是 卖出量 * 卖出价 才对，没搞清楚为什么...
                self.log(f"卖单执行: 卖出成交量={order.executed.size}, 卖出成交价={order.executed.price:.2f}, "
                         f"订单计算金额={abs(order.executed.size) * order.executed.price:.2f}, "
                         f"框架计算金额={order.executed.value:.2f}, "  # 个人理解，这个值应该叫做持仓成本
                         f"手续费={order.executed.comm:.2f}, "
                         f"毛盈亏={order.executed.pnl:.2f}") # 毛盈利，未扣除手续费
                if order.executed.pnl > 0:
                    self.log(f"^_^ ^_^ ^_^ ^_^ 卖单盈利: 盈利金额={order.executed.pnl:.2f}")
                else:
                    self.log(f"-_- -_- -_- -_- 卖单亏损: 亏损金额={order.executed.pnl:.2f}")

            self.order = None
        # 订单取消、保证金不足或拒绝时，打印日志并重置订单
        # 需要一个更好的方式来处理保证金不足的情况，比如减少下单量。
        elif order.status == order.Margin:
            self.log(f"[警告] 保证金不足，订单未能完全成交: {order.getstatusname()}")
           # self.log(f"订单详情: {order}")
            self.log(f"订单创建的数量: {order.created.size}")
            self.log(f"当前账户总市值: {self.broker.getvalue()}")
            '''
            # 获取原订单的目标百分比并减少到 80%
            if order.created.size > 0:
                reduced_target = (0.8 * order.created.size * order.created.price)/self.broker.getvalue()
                self.log(f"重新提交订单，目标调整为 80%: {reduced_target}")
                self.order = self.order_target_percent(target=reduced_target)
            else:
                self.log("[错误] 无法重新提交订单，订单创建数量为 0 或无效")
            '''
            self.order = None

        elif order.status == order.Rejected:
            self.log(f"[警告] 订单被拒绝: {order.getstatusname()}")
        #    self.log(f"订单详情: {order}")
            self.order = None
        elif order.status == order.Canceled:
        #    self.log(f"订单已取消: {order.getstatusname()}")
            self.order = None        

    def next(self):
        """
        每根Bar调用一次：
        - 如果已有订单挂单，则不执行新交易；
        - 根据当前 RSI 信号决定是否全仓买入或清仓。
        """
        dt = self.data.datetime.datetime(0)
        # 可选：打印当前账户可用的现金、持仓市值和收盘价信息
        #cash = self.broker.getcash() # 当前可用现金
        #value = self.broker.getvalue() # 当前总市值 = 现金 + 持仓市值
        #pos_size = self.position.size
        #self.log(f"当前Bar={dt}, 收盘价={self.dataclose[0]:.2f}, 资金={cash:.2f}, 总市值={value:.2f}, 持仓数={pos_size}")

        # 如果已有挂单，直接返回
        if self.order:
            return

        current_rsi = self.rsi[0]

        # 无持仓时，RSI低于超卖阈值则满仓买入
        if not self.position:
            if current_rsi < self.params.oversold:
                self.log(f"RSI={current_rsi:.2f} < 超卖阈值({self.params.oversold:.2f})，准备满仓买入，当前价格={self.dataclose[0]:.2f}")
                # 目标式下单，不能用于限价单。只能用于市价单（即 exectype=bt.Order.Market，默认）
                self.order = self.order_target_percent(target=1.0)
        # 有持仓时，RSI高于超买阈值则清仓
        else:
            if current_rsi > self.params.overbought:
                self.log(f"RSI={current_rsi:.2f} > 超买阈值({self.params.overbought:.2f})，准备清仓，当前价格={self.dataclose[0]:.2f}")
                self.order = self.order_target_percent(target=0.0)

    def stop(self):
        """回测结束时输出最终市值。"""
        # 当前总市值 = 现金 + 持仓市值
        self.log(f"回测结束 - 最终总市值: {self.broker.getvalue():.2f}")
