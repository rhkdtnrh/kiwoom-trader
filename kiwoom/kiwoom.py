import csv
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from PyQt5.QtTest import *
from pytz import timezone

import analysis.checkBuySellList
from config.errorCode import *
from config.kiwoomType import *
from config.log_class import *
from config.message_bot import *


class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self.realType = RealType()
        self.logging = Logging()
        self.myMsg = MyMsg()  # 슬랙 동작
        self.market_finish_trigger = 0

        # print("Kiwoom() class start.")
        self.logging.logger.debug("Kiwoom() class start.")

        ####### event loop를 실행하기 위한 변수 모음
        self.login_event_loop = QEventLoop()  # 로그인 요청용 이벤트 루프
        self.detail_account_info_event_loop = QEventLoop()  # 예수금 요청용 이벤트 루프
        self.calculator_event_loop = QEventLoop()
        #########################################

        ########### 전체 종목 관리
        self.all_stock_dict = {}
        ###########################

        ####### 계좌 관련된 변수
        self.account_stock_dict = {}  # 현재 보유중인 종목
        self.not_account_stock_dict = {}  # 미체결 종목
        self.account_num = None  # 계좌번호 담아줄 변수
        self.deposit = 0  # 예수금
        self.use_money = 0  # 실제 투자에 사용할 금액
        self.use_money_percent = 0.2  # 예수금에서 실제 사용할 비율
        self.output_deposit = 0  # 출력가능 금액
        self.total_profit_loss_money = 0  # 총평가손익금액
        self.total_profit_loss_rate = 0.0  # 총수익률(%)
        ########################################

        ######## 종목 정보 가져오기
        self.portfolio_stock_dict = {}  # 전일 계산된 매수 종목 후보
        self.jango_dict = {}  # 실시간 매수한 종목
        ########################

        #### 주문 종목 처리
        self.buy_order_list = []
        self.sell_order_list = []

        ########### 종목 분석 용
        self.calcul_data = []
        ##########################################

        ####### 요청 스크린 번호
        self.screen_my_info = "2000"  # 계좌 관련한 스크린 번호
        self.screen_calculation_stock = "4000"  # 계산용 스크린 번호
        self.screen_real_stock = "5000"  # 종목별 할당할 스크린 번호
        self.screen_meme_stock = "6000"  # 종목별 할당할 주문용 스크린 번호
        self.screen_start_stop_real = "1000"  # 장 시작/종료 실시간 스크린 번호
        ########################################

        ######### 초기 셋팅 함수들 바로 실행
        self.get_ocx_instance()  # OCX 방식을 파이썬에 사용할 수 있게 반환해 주는 함수 실행
        self.event_slots()  # 키움과 연결하기 위한 시그널 / 슬롯 모음
        self.real_event_slot()  # 실시간 이벤트 시그널 / 슬롯 연결
        self.signal_login_commConnect()  # 로그인 요청 함수 포함
        self.get_account_info()  # 계좌번호 가져오기

        self.detail_account_info()  # 예수금 요청 시그널 포함
        self.detail_account_mystock()  # 계좌평가잔고내역 가져오기
        QTimer.singleShot(5000, self.not_concluded_account)  # 5초 뒤에 미체결 종목들 가져오기 실행
        #########################################

        QTest.qWait(10000)
        self.read_module_a()
        self.read_module_b()
        self.read_module_c()
        self.candidate_count = len(self.portfolio_stock_dict)  # 매수 종목 개수
        self.screen_number_setting()

        message_string = []
        message_string2 = []
        message_string3 = []
        i = 0
        if len(self.account_stock_dict) == 0:
            message_string.append("[보유 종목 없음]")
            self.myMsg.send_msg_telegram('\n'.join(message_string))
        else:
            message_string.append("[보유 종목 리스트]")
            for code in self.account_stock_dict.keys():
                code_name = self.account_stock_dict[code]["종목명"]
                quantity = self.account_stock_dict[code]["보유수량"]
                buy_price = self.account_stock_dict[code]["매입가"]
                current_price = self.account_stock_dict[code]["현재가"]
                profit_rate = self.account_stock_dict[code]["수익률(%)"]
                total_buy_price = quantity * buy_price
                total_current_price = quantity * current_price
                profit = total_current_price - total_buy_price
                if i % 3 == 0:
                    message_string.append("종목명: %s\n보유수량: %d\n매입가: %d\n현재가: %d\n수익률: %f\n매입금액: %d\n평가금액: %d\n수익: %d" % (
                        code_name, quantity, buy_price, current_price, profit_rate, total_buy_price,
                        total_current_price,
                        profit))
                    message_string.append("-------------------------------------")
                elif i % 3 == 1:
                    message_string3.append(
                        "종목명: %s\n보유수량: %d\n매입가: %d\n현재가: %d\n수익률: %f\n매입금액: %d\n평가금액: %d\n수익: %d" % (
                            code_name, quantity, buy_price, current_price, profit_rate, total_buy_price,
                            total_current_price,
                            profit))
                    message_string3.append("-------------------------------------")
                else:
                    message_string2.append(
                        "종목명: %s\n보유수량: %d\n매입가: %d\n현재가: %d\n수익률: %f\n매입금액: %d\n평가금액: %d\n수익: %d" % (
                            code_name, quantity, buy_price, current_price, profit_rate, total_buy_price,
                            total_current_price,
                            profit))
                    message_string2.append("-------------------------------------")
                i = i + 1
            self.myMsg.send_msg_telegram('\n'.join(message_string))
            self.myMsg.send_msg_telegram('\n'.join(message_string2))
            self.myMsg.send_msg_telegram('\n'.join(message_string3))

        message_string = []
        if len(self.not_account_stock_dict) == 0:
            message_string.append("[미체결 종목 없음]")
        else:
            message_string.append("[미체결 종목 리스트]")
            for order_no in self.not_account_stock_dict.keys():
                code_name = self.not_account_stock_dict[order_no]["종목명"]
                order_status = self.not_account_stock_dict[order_no]["주문상태"]
                order_quantity = self.not_account_stock_dict[order_no]["주문수량"]
                order_price = self.not_account_stock_dict[order_no]["주문가격"]
                order_gubun = self.not_account_stock_dict[order_no]["주문구분"]
                not_quantity = int(self.not_account_stock_dict[order_no]["미체결수량"])
                ok_quantity = int(self.not_account_stock_dict[order_no]["체결량"])
                print(ok_quantity)
                message_string.append(
                    "종목명: %s\n주문번호: %d\n주문상태: %s\n주문수량: %d\n주문가격: %d\n주문구분: %s\n미체결수량: %d\n체결량: %d" % (
                        code_name, order_no, order_status, order_quantity, order_price, order_gubun, not_quantity,
                        ok_quantity))
                message_string.append("-------------------------------------")
        self.myMsg.send_msg_telegram('\n'.join(message_string))

        message_string = []
        if len(self.portfolio_stock_dict) == 0:
            message_string.append("[매수 후보 종목 없음]")
        else:
            message_string.append("[매수 후보 종목 리스트]")
            for code in self.portfolio_stock_dict.keys():
                try:
                    code_name = self.portfolio_stock_dict[code]["종목명"]
                    stock_price = self.portfolio_stock_dict[code]["현재가"]
                    logic = self.portfolio_stock_dict[code]["Logic"]
                    message_string.append("종목명: %s\n최근가격: %d\n로직: %s" % (code_name, stock_price, logic))
                    message_string.append("-------------------------------------")
                except KeyError:
                    continue
        self.myMsg.send_msg_telegram('\n'.join(message_string))

        QTest.qWait(5000)

        # 실시간 수신 관련 함수
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)", self.screen_start_stop_real, '',
                         self.realType.REALTYPE['장시작시간']['장운영구분'], "0")

        for code in self.portfolio_stock_dict.keys():
            screen_num = self.portfolio_stock_dict[code]['스크린번호']
            fids = self.realType.REALTYPE['주식체결']['체결시간']
            self.dynamicCall("SetRealReg(QString, QString, QString, QString)", screen_num, code, fids, "1")

        self.myMsg.send_msg_telegram(msg="주식 자동화 프로그램 동작")

        # self.after_market()
        # self.buy_list_process()
        # self.after_market()
        # QTimer.singleShot(5000, self.after_market)

    def get_ocx_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")  # 레지스트리에 저장된 API 모듈 불러오기

    def event_slots(self):
        self.OnEventConnect.connect(self.login_slot)  # 로그인 관련 이벤트
        self.OnReceiveTrData.connect(self.trdata_slot)  # 트랜잭션 요청 관련 이벤트
        self.OnReceiveMsg.connect(self.msg_slot)

    def real_event_slot(self):
        self.OnReceiveRealData.connect(self.realdata_slot)  # 실시간 이벤트 연결
        self.OnReceiveChejanData.connect(self.chejan_slot)  # 종목 주문체결 관련한 이벤트

    def signal_login_commConnect(self):
        self.dynamicCall("CommConnect()")  # 로그인 요청 시그널

        self.login_event_loop.exec_()  # 이벤트 루프 실행

    def login_slot(self, err_code):
        self.logging.logger.debug(errors(err_code)[1])

        # 로그인 처리가 완료됐으면 이벤트 루프를 종료한다.
        self.login_event_loop.exit()

    def get_account_info(self):
        account_list = self.dynamicCall("GetLoginInfo(QString)", "ACCNO")  # 계좌번호 반환
        account_num = account_list.split(';')[1]  # a;b;c  [a, b, c]

        self.account_num = account_num

        self.logging.logger.debug("계좌번호 : %s" % account_num)
        self.myMsg.send_msg_telegram("계좌번호 : %s" % account_num)

    def detail_account_info(self, sPrevNext="0"):
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호", "0000")
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(QString, QString)", "조회구분", "1")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "예수금상세현황요청", "opw00001", sPrevNext,
                         self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

    def detail_account_mystock(self, sPrevNext="0"):
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호", "0000")
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(QString, QString)", "조회구분", "1")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "계좌평가잔고내역요청", "opw00018", sPrevNext,
                         self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

    def not_concluded_account(self, sPrevNext="0"):
        self.logging.logger.debug("미체결 종목 요청")
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(QString, QString)", "체결구분", "1")
        self.dynamicCall("SetInputValue(QString, QString)", "매매구분", "0")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "실시간미체결요청", "opt10075", sPrevNext,
                         self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

    def trdata_slot(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):
        if sRQName == "예수금상세현황요청":
            deposit = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "예수금")
            self.deposit = int(deposit)

            use_money = float(self.deposit) * self.use_money_percent
            self.use_money = int(use_money)
            # self.use_money = self.use_money / 4

            output_deposit = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0,
                                              "출금가능금액")
            self.output_deposit = int(output_deposit)

            self.logging.logger.debug("예수금 : %s" % self.output_deposit)
            self.myMsg.send_msg_telegram("예수금 : %s" % self.output_deposit)

            self.stop_screen_cancel(self.screen_my_info)

            self.detail_account_info_event_loop.exit()

        elif sRQName == "계좌평가잔고내역요청":
            total_money = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "추정예탁자산")
            self.total_money = int(total_money)
            total_evaluated_money = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0,
                                                     "총평가금액")
            self.total_evaluated_money = int(total_evaluated_money)
            total_buy_money = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0,
                                               "총매입금액")  # 출력 : 000000000746100
            self.total_buy_money = int(total_buy_money)
            total_profit_loss_money = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName,
                                                       0, "총평가손익금액")  # 출력 : 000000000009761
            self.total_profit_loss_money = int(total_profit_loss_money)
            total_profit_loss_rate = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName,
                                                      0, "총수익률(%)")  # 출력 : 000000001.31
            self.total_profit_loss_rate = float(total_profit_loss_rate) / 100

            self.logging.logger.debug("[계좌평가잔고] 총자산 : %d <> 총평가금액 : %d <> 총매입금액 : %d <> 총평가손익금액 : %d <> 총수익률 : %f" % (
            self.total_money, self.total_evaluated_money, self.total_buy_money, self.total_profit_loss_money,
            self.total_profit_loss_rate))
            self.myMsg.send_msg_telegram("[계좌평가잔고]\n 총자산 : %d\n 총평가금액 : %d\n 총매입금액 : %d\n 총평가손익금액 : %d\n 총수익률 : %f" % (
            self.total_money, self.total_evaluated_money, self.total_buy_money, self.total_profit_loss_money,
            self.total_profit_loss_rate))

            rows = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)
            for i in range(rows):
                code = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목번호")
                code = code.strip()[1:]

                code_nm = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목명")
                stock_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                  "보유수량")
                buy_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "매입가")
                learn_rate = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                              "수익률(%)")
                current_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                 "현재가")
                total_chegual_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName,
                                                       i, "매입금액")
                possible_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                     "매매가능수량")

                if code in self.account_stock_dict:
                    pass
                else:
                    self.account_stock_dict[code] = {}

                code_nm = code_nm.strip()
                stock_quantity = int(stock_quantity.strip())
                buy_price = int(buy_price.strip())
                learn_rate = float(learn_rate.strip()) / 100
                current_price = int(current_price.strip())
                total_chegual_price = int(total_chegual_price.strip())
                possible_quantity = int(possible_quantity.strip())

                self.logging.logger.debug(
                    "종목번호: %s - 종목명: %s - 보유수량: %d - 매입가: %d - 수익률: %f - 현재가: %d - 매입금액: %d - 매매가능수량: %d" % (
                        code, code_nm, stock_quantity, buy_price, learn_rate, current_price, total_chegual_price,
                        possible_quantity))

                self.account_stock_dict[code].update({"종목명": code_nm})
                self.account_stock_dict[code].update({"보유수량": stock_quantity})
                self.account_stock_dict[code].update({"매입가": buy_price})
                self.account_stock_dict[code].update({"수익률(%)": learn_rate})
                self.account_stock_dict[code].update({"현재가": current_price})
                self.account_stock_dict[code].update({"매입금액": total_chegual_price})
                self.account_stock_dict[code].update({"매매가능수량": possible_quantity})

            self.logging.logger.debug("sPreNext : %s" % sPrevNext)
            self.logging.logger.debug("계좌에 가지고 있는 종목은 %s " % rows)

            if sPrevNext == "2":
                self.detail_account_mystock(sPrevNext="2")
            else:
                self.detail_account_info_event_loop.exit()

        elif sRQName == "실시간미체결요청":
            rows = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)

            for i in range(rows):
                code = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목코드")

                code_nm = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목명")
                order_no = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문번호")
                order_status = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                "주문상태")  # 접수,확인,체결
                order_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                  "주문수량")
                order_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                               "주문가격")
                order_gubun = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                               "주문구분")  # -매도, +매수, -매도정정, +매수정정
                not_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                "미체결수량")
                ok_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                               "체결량")

                code = code.strip()
                code_nm = code_nm.strip()
                order_no = int(order_no.strip())
                order_status = order_status.strip()
                order_quantity = int(order_quantity.strip())
                order_price = int(order_price.strip())
                order_gubun = order_gubun.strip().lstrip('+').lstrip('-')
                not_quantity = int(not_quantity.strip())
                ok_quantity = int(ok_quantity.strip())

                if order_no in self.not_account_stock_dict:
                    pass
                else:
                    self.not_account_stock_dict[order_no] = {}

                self.not_account_stock_dict[order_no].update({'종목코드': code})
                self.not_account_stock_dict[order_no].update({'종목명': code_nm})
                self.not_account_stock_dict[order_no].update({'주문번호': order_no})
                self.not_account_stock_dict[order_no].update({'주문상태': order_status})
                self.not_account_stock_dict[order_no].update({'주문수량': order_quantity})
                self.not_account_stock_dict[order_no].update({'주문가격': order_price})
                self.not_account_stock_dict[order_no].update({'주문구분': order_gubun})
                self.not_account_stock_dict[order_no].update({'미체결수량': not_quantity})
                self.not_account_stock_dict[order_no].update({'체결량': ok_quantity})

                self.logging.logger.debug("미체결 종목 : %s " % self.not_account_stock_dict[order_no])

            self.detail_account_info_event_loop.exit()

    def stop_screen_cancel(self, sScrNo=None):
        self.dynamicCall("DisconnectRealData(QString)", sScrNo)  # 스크린 번호 연결 끊기

    def get_code_list_by_market(self, market_code):
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market_code)
        code_list = code_list.split(';')[:-1]
        return code_list

    def read_module_a(self):
        today = datetime.datetime.today().astimezone(timezone('Asia/Seoul'))
        if today.strftime('%A') == 'Monday':
            yesterday = (today - timedelta(3)).strftime("%Y%m%d")
        else:
            yesterday = (today - timedelta(1)).strftime("%Y%m%d")

        if os.path.exists("files/buy/Module_A_" + yesterday + ".csv"):  # 해당 경로에 파일이 있는지 체크한다.
            f = open("files/buy/Module_A_" + yesterday + ".csv", "r", encoding="utf8")
            csv_data = csv.reader(f)
            next(csv_data)  # csv header skip
            for line in csv_data:  # 줄바꿈된 내용들이 한줄 씩 읽어와진다.
                if line != "":
                    stock_code = line[8]
                    stock_name = line[7]
                    stock_price = int(line[4])
                    stock_price = abs(stock_price)
                    if stock_code not in self.portfolio_stock_dict.keys():
                        self.portfolio_stock_dict.update(
                            {stock_code: {"종목명": stock_name, "현재가": stock_price, "Logic": "A"}})
            f.close()

    def read_module_b(self):
        today = datetime.datetime.today().astimezone(timezone('Asia/Seoul'))
        if today.strftime('%A') == 'Monday':
            yesterday = (today - timedelta(3)).strftime("%Y%m%d")
        else:
            yesterday = (today - timedelta(1)).strftime("%Y%m%d")

        if os.path.exists("files/buy/Module_B_" + yesterday + ".csv"):  # 해당 경로에 파일이 있는지 체크한다.
            f = open("files/buy/Module_B_" + yesterday + ".csv", "r", encoding="utf8")
            csv_data = csv.reader(f)
            next(csv_data)  # csv header skip
            for line in csv_data:  # 줄바꿈된 내용들이 한줄 씩 읽어와진다.
                if line != "":
                    stock_code = line[8]
                    stock_name = line[7]
                    stock_price = int(line[4])
                    stock_price = abs(stock_price)
                    if stock_code not in self.portfolio_stock_dict.keys():
                        self.portfolio_stock_dict.update(
                            {stock_code: {"종목명": stock_name, "현재가": stock_price, "Logic": "B"}})
            f.close()

    def read_module_c(self):
        today = datetime.datetime.today().astimezone(timezone('Asia/Seoul'))
        if today.strftime('%A') == 'Monday':
            yesterday = (today - timedelta(3)).strftime("%Y%m%d")
        else:
            yesterday = (today - timedelta(1)).strftime("%Y%m%d")

        if os.path.exists("files/buy/Module_C_" + yesterday + ".csv"):  # 해당 경로에 파일이 있는지 체크한다.
            f = open("files/buy/Module_C_" + yesterday + ".csv", "r", encoding="utf8")
            csv_data = csv.reader(f)
            next(csv_data)  # csv header skip
            for line in csv_data:  # 줄바꿈된 내용들이 한줄 씩 읽어와진다.
                if line != "":
                    stock_code = line[8]
                    stock_name = line[7]
                    stock_price = int(line[4])
                    stock_price = abs(stock_price)
                    if stock_code not in self.portfolio_stock_dict.keys():
                        self.portfolio_stock_dict.update(
                            {stock_code: {"종목명": stock_name, "현재가": stock_price, "Logic": "C"}})
            f.close()

    def merge_dict(self):
        self.all_stock_dict.update({"계좌평가잔고내역": self.account_stock_dict})
        self.all_stock_dict.update({'미체결종목': self.not_account_stock_dict})
        self.all_stock_dict.update({'포트폴리오종목': self.portfolio_stock_dict})

    def screen_number_setting(self):
        screen_overwrite = []

        # 계좌평가잔고내역에 있는 종목들
        for code in self.account_stock_dict.keys():
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 미체결에 있는 종목들
        for order_number in self.not_account_stock_dict.keys():
            code = self.not_account_stock_dict[order_number]['종목코드']

            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 포트폴리오에 있는 종목들
        for code in self.portfolio_stock_dict.keys():
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 스크린 번호 할당
        cnt = 0
        for code in screen_overwrite:
            temp_screen = int(self.screen_real_stock)
            meme_screen = int(self.screen_meme_stock)

            if (cnt % 50) == 0:
                temp_screen += 1
                self.screen_real_stock = str(temp_screen)

            if (cnt % 50) == 0:
                meme_screen += 1
                self.screen_meme_stock = str(meme_screen)

            if code in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict[code].update({"스크린번호": str(self.screen_real_stock)})
                self.portfolio_stock_dict[code].update({"주문용스크린번호": str(self.screen_meme_stock)})

            elif code not in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict.update(
                    {code: {"스크린번호": str(self.screen_real_stock), "주문용스크린번호": str(self.screen_meme_stock)}})

            cnt += 1

        self.logging.logger.debug(self.portfolio_stock_dict)

    def realdata_slot(self, sCode, sRealType, sRealData):
        if sRealType == "장시작시간":
            fid = self.realType.REALTYPE[sRealType]['장운영구분']  # (0:장시작전, 2:장종료전(20분), 3:장시작, 4,8:장종료(30분), 9:장마감)
            value = self.dynamicCall("GetCommRealData(QString, int)", sCode, fid)

            if value == '0':
                self.logging.logger.debug("장 시작 전")
                # self.myMsg.send_msg_telegram("장 시작 전")

            elif value == '3':
                self.logging.logger.debug("장 시작")
                self.myMsg.send_msg_telegram("장 시작")

            elif value == "2":
                self.market_finish_trigger += 1
                if self.market_finish_trigger == 1:
                    self.logging.logger.debug("장 종료, 동시호가로 넘어감")
                    self.myMsg.send_msg_telegram("장 종료, 동시호가로 넘어감")
                    QTimer.singleShot(5000, self.after_market)

            elif value == "4":
                self.logging.logger.debug("3시30분 장 종료")
                self.myMsg.send_msg_telegram("3시30분 장 종료")

                for code in self.portfolio_stock_dict.keys():
                    self.dynamicCall("SetRealRemove(QString, QString)", self.portfolio_stock_dict[code]['스크린번호'], code)

                QTest.qWait(1800000)
                self.buy_list_process()


        elif sRealType == "주식체결":
            a = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                                 self.realType.REALTYPE[sRealType]['체결시간'])  # 출력 HHMMSS
            b = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                                 self.realType.REALTYPE[sRealType]['현재가'])  # 출력 : +(-)2520
            b = abs(int(b))

            c = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                                 self.realType.REALTYPE[sRealType]['전일대비'])  # 출력 : +(-)2520
            c = abs(int(c))

            d = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                                 self.realType.REALTYPE[sRealType]['등락율'])  # 출력 : +(-)12.98
            d = float(d)

            e = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                                 self.realType.REALTYPE[sRealType]['(최우선)매도호가'])  # 출력 : +(-)2520
            e = abs(int(e))

            f = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                                 self.realType.REALTYPE[sRealType]['(최우선)매수호가'])  # 출력 : +(-)2515
            f = abs(int(f))

            g = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                                 self.realType.REALTYPE[sRealType]['거래량'])  # 출력 : +240124 매수일때, -2034 매도일 때
            g = abs(int(g))

            h = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                                 self.realType.REALTYPE[sRealType]['누적거래량'])  # 출력 : 240124
            h = abs(int(h))

            i = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                                 self.realType.REALTYPE[sRealType]['고가'])  # 출력 : +(-)2530
            i = abs(int(i))

            j = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                                 self.realType.REALTYPE[sRealType]['시가'])  # 출력 : +(-)2530
            j = abs(int(j))

            k = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                                 self.realType.REALTYPE[sRealType]['저가'])  # 출력 : +(-)2530
            k = abs(int(k))

            self.portfolio_stock_dict[sCode].update({"체결시간": a})
            self.portfolio_stock_dict[sCode].update({"현재가": b})
            self.portfolio_stock_dict[sCode].update({"전일대비": c})
            self.portfolio_stock_dict[sCode].update({"등락율": d})
            self.portfolio_stock_dict[sCode].update({"(최우선)매도호가": e})
            self.portfolio_stock_dict[sCode].update({"(최우선)매수호가": f})
            self.portfolio_stock_dict[sCode].update({"거래량": g})
            self.portfolio_stock_dict[sCode].update({"누적거래량": h})
            self.portfolio_stock_dict[sCode].update({"고가": i})
            self.portfolio_stock_dict[sCode].update({"시가": j})
            self.portfolio_stock_dict[sCode].update({"저가": k})

            if sCode in self.account_stock_dict.keys() and sCode not in self.jango_dict.keys() and sCode not in self.sell_order_list:

                asd = self.account_stock_dict[sCode]
                meme_rate = (b - asd['매입가']) / asd['매입가'] * 100

                if asd['매매가능수량'] > 0 and (meme_rate > 15 or meme_rate < -10):
                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                        ["신규매도", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 2, sCode,
                         asd['매매가능수량'], 0, self.realType.SENDTYPE['거래구분']['시장가'], ""]
                    )

                    if order_success == 0:
                        self.logging.logger.debug("매도주문 전달 성공 > %s, 현재가 : %d, 매입가 : %d, 주문수량 : %d" % (
                        self.account_stock_dict[sCode]["종목명"], b, self.account_stock_dict[sCode]["매입가"],
                        self.account_stock_dict[sCode]["매매가능수량"]))
                        self.myMsg.send_msg_telegram("매도주문 전달 성공 > %s, 현재가 : %d, 매입가 : %d, 주문수량 : %d" % (
                        self.account_stock_dict[sCode]["종목명"], b, self.account_stock_dict[sCode]["매입가"],
                        self.account_stock_dict[sCode]["매매가능수량"]))
                        del self.account_stock_dict[sCode]
                        self.sell_order_list.append(sCode)
                    else:
                        self.logging.logger.debug("매도주문 전달 실패 > %s, 현재가 : %d, 매입가 : %d, 주문수량 : %d" % (
                        self.account_stock_dict[sCode]["종목명"], b, self.account_stock_dict[sCode]["매입가"],
                        self.account_stock_dict[sCode]["매매가능수량"]))
                        self.myMsg.send_msg_telegram("매도주문 전달 실패 > %s, 현재가 : %d, 매입가 : %d, 주문수량 : %d" % (
                        self.account_stock_dict[sCode]["종목명"], b, self.account_stock_dict[sCode]["매입가"],
                        self.account_stock_dict[sCode]["매매가능수량"]))

            elif sCode in self.jango_dict.keys() and sCode not in self.sell_order_list:

                jd = self.jango_dict[sCode]
                meme_rate = (b - jd['매입단가']) / jd['매입단가'] * 100

                if jd['주문가능수량'] > 0 and (meme_rate > 15 or meme_rate < -10):
                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                        ["신규매도", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 2, sCode, jd['주문가능수량'],
                         0, self.realType.SENDTYPE['거래구분']['시장가'], ""]
                    )

                    if order_success == 0:
                        self.logging.logger.debug("매도주문 전달 성공 > %s, 현재가 : %d, 매입가 : %d, 주문수량 : %d" % (
                        self.jango_dict[sCode]["종목명"], b, self.jango_dict[sCode]["매입단가"],
                        self.jango_dict[sCode]["주문가능수량"]))
                        self.myMsg.send_msg_telegram("매도주문 전달 성공 > %s, 현재가 : %d, 매입가 : %d, 주문수량 : %d" % (
                        self.jango_dict[sCode]["종목명"], b, self.jango_dict[sCode]["매입단가"],
                        self.jango_dict[sCode]["주문가능수량"]))
                        self.sell_order_list.append(sCode)
                    else:
                        self.logging.logger.debug("매도주문 전달 실패 > %s, 현재가 : %d, 매입가 : %d, 주문수량 : %d" % (
                        self.jango_dict[sCode]["종목명"], b, self.jango_dict[sCode]["매입단가"],
                        self.jango_dict[sCode]["주문가능수량"]))
                        self.myMsg.send_msg_telegram("매도주문 전달 실패 > %s, 현재가 : %d, 매입가 : %d, 주문수량 : %d" % (
                        self.jango_dict[sCode]["종목명"], b, self.jango_dict[sCode]["매입단가"],
                        self.jango_dict[sCode]["주문가능수량"]))

            elif d > 1.0 and sCode not in self.jango_dict and sCode not in self.buy_order_list:
                self.logging.logger.debug("매수조건 통과 > %s" % self.portfolio_stock_dict[sCode]["종목명"])
                self.myMsg.send_msg_telegram("매수조건 통과 > %s" % self.portfolio_stock_dict[sCode]["종목명"])

                result = (self.use_money * (
                        1 / self.candidate_count)) / e  # 매수 금액 예산을 매수 종목 후보 개수로 나눠 종목당 매수 금액을 구하고, 이것을 종목당 최우선 매도호가로 나누어 매수량을 정한다.
                quantity = int(result * 0.9)

                order_success = self.dynamicCall(
                    "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                    ["신규매수", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 1, sCode, quantity, 0,
                     self.realType.SENDTYPE['거래구분']['시장가'], ""]
                )

                if order_success == 0:
                    self.logging.logger.debug(
                        "매수주문 전달 성공 > %s, 현재가 : %d, 주문수량 : %d" % (self.portfolio_stock_dict[sCode]["종목명"], b, quantity))
                    self.myMsg.send_msg_telegram(
                        "매수주문 전달 성공 > %s, 현재가 : %d, 주문수량 : %d" % (self.portfolio_stock_dict[sCode]["종목명"], b, quantity))
                    self.buy_order_list.append(sCode)
                else:
                    self.logging.logger.debug(
                        "매수주문 전달 실패 > %s, 현재가 : %d, 주문수량 : %d" % (self.portfolio_stock_dict[sCode]["종목명"], b, quantity))
                    self.myMsg.send_msg_telegram(
                        "매수주문 전달 실패 > %s, 현재가 : %d, 주문수량 : %d" % (self.portfolio_stock_dict[sCode]["종목명"], b, quantity))

            not_meme_list = list(self.not_account_stock_dict)
            for order_num in not_meme_list:

                code = self.not_account_stock_dict[order_num]["종목코드"]
                meme_price = self.not_account_stock_dict[order_num]['주문가격']
                not_quantity = self.not_account_stock_dict[order_num]['미체결수량']
                order_gubun = self.not_account_stock_dict[order_num]['주문구분']

                if code == sCode and order_gubun == "매수" and not_quantity > 0 and (e - meme_price + 1) / (
                        meme_price + 1) > 0.1 and meme_price != 0:
                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                        ["매수취소", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 3, code, 0, 0,
                         self.realType.SENDTYPE['거래구분']['시장가'], order_num]
                    )

                    if order_success == 0:
                        self.logging.logger.debug("매수취소 전달 성공 > %s" % self.not_account_stock_dict[order_num]["종목명"])
                        self.myMsg.send_msg_telegram("매수취소 전달 성공 > %s" % self.not_account_stock_dict[order_num]["종목명"])
                    else:
                        self.logging.logger.debug("매수취소 전달 실패 > %s" % self.not_account_stock_dict[order_num]["종목명"])
                        self.myMsg.send_msg_telegram("매수취소 전달 실패 > %s" % self.not_account_stock_dict[order_num]["종목명"])

                elif not_quantity == 0:
                    del self.not_account_stock_dict[order_num]

    def chejan_slot(self, sGubun, nItemCnt, sFidList):
        if int(sGubun) == 0:  # 주문체결
            account_num = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['계좌번호'])
            sCode = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['종목코드'])[1:]
            stock_name = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['종목명'])
            stock_name = stock_name.strip()

            origin_order_number = self.dynamicCall("GetChejanData(int)",
                                                   self.realType.REALTYPE['주문체결']['원주문번호'])  # 출력 : defaluse : "000000"
            order_number = self.dynamicCall("GetChejanData(int)",
                                            self.realType.REALTYPE['주문체결']['주문번호'])  # 출럭: 0115061 마지막 주문번호

            order_status = self.dynamicCall("GetChejanData(int)",
                                            self.realType.REALTYPE['주문체결']['주문상태'])  # 출력: 접수, 확인, 체결
            order_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문수량'])  # 출력 : 3
            order_quan = int(order_quan)

            order_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문가격'])  # 출력: 21000
            order_price = int(order_price)

            not_chegual_quan = self.dynamicCall("GetChejanData(int)",
                                                self.realType.REALTYPE['주문체결']['미체결수량'])  # 출력: 15, default: 0
            not_chegual_quan = int(not_chegual_quan)

            order_gubun = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문구분'])  # 출력: -매도, +매수
            order_gubun = order_gubun.strip().lstrip('+').lstrip('-')

            chegual_time_str = self.dynamicCall("GetChejanData(int)",
                                                self.realType.REALTYPE['주문체결']['주문/체결시간'])  # 출력: '151028'

            chegual_price = self.dynamicCall("GetChejanData(int)",
                                             self.realType.REALTYPE['주문체결']['체결가'])  # 출력: 2110 default : ''
            if chegual_price == '':
                chegual_price = 0
            else:
                chegual_price = int(chegual_price)

            chegual_quantity = self.dynamicCall("GetChejanData(int)",
                                                self.realType.REALTYPE['주문체결']['체결량'])  # 출력: 5 default : ''
            if chegual_quantity == '':
                chegual_quantity = 0
            else:
                chegual_quantity = int(chegual_quantity)

            current_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['현재가'])  # 출력: -6000
            current_price = abs(int(current_price))

            first_sell_price = self.dynamicCall("GetChejanData(int)",
                                                self.realType.REALTYPE['주문체결']['(최우선)매도호가'])  # 출력: -6010
            first_sell_price = abs(int(first_sell_price))

            first_buy_price = self.dynamicCall("GetChejanData(int)",
                                               self.realType.REALTYPE['주문체결']['(최우선)매수호가'])  # 출력: -6000
            first_buy_price = abs(int(first_buy_price))

            ######## 새로 들어온 주문이면 주문번호 할당
            if order_number not in self.not_account_stock_dict.keys():
                self.not_account_stock_dict.update({order_number: {}})

            self.not_account_stock_dict[order_number].update({"종목코드": sCode})
            self.not_account_stock_dict[order_number].update({"주문번호": order_number})
            self.not_account_stock_dict[order_number].update({"종목명": stock_name})
            self.not_account_stock_dict[order_number].update({"주문상태": order_status})
            self.not_account_stock_dict[order_number].update({"주문수량": order_quan})
            self.not_account_stock_dict[order_number].update({"주문가격": order_price})
            self.not_account_stock_dict[order_number].update({"미체결수량": not_chegual_quan})
            self.not_account_stock_dict[order_number].update({"원주문번호": origin_order_number})
            self.not_account_stock_dict[order_number].update({"주문구분": order_gubun})
            self.not_account_stock_dict[order_number].update({"주문/체결시간": chegual_time_str})
            self.not_account_stock_dict[order_number].update({"체결가": chegual_price})
            self.not_account_stock_dict[order_number].update({"체결량": chegual_quantity})
            self.not_account_stock_dict[order_number].update({"현재가": current_price})
            self.not_account_stock_dict[order_number].update({"(최우선)매도호가": first_sell_price})
            self.not_account_stock_dict[order_number].update({"(최우선)매수호가": first_buy_price})

        elif int(sGubun) == 1:  # 잔고
            account_num = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['계좌번호'])
            sCode = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['종목코드'])[1:]

            stock_name = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['종목명'])
            stock_name = stock_name.strip()

            current_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['현재가'])
            current_price = abs(int(current_price))

            stock_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['보유수량'])
            stock_quan = int(stock_quan)

            like_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['주문가능수량'])
            like_quan = int(like_quan)

            buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['매입단가'])
            buy_price = abs(int(buy_price))

            total_buy_price = self.dynamicCall("GetChejanData(int)",
                                               self.realType.REALTYPE['잔고']['총매입가'])  # 계좌에 있는 종목의 총매입가
            total_buy_price = int(total_buy_price)

            meme_gubun = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['매도매수구분'])
            meme_gubun = self.realType.REALTYPE['매도수구분'][meme_gubun]

            first_sell_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['(최우선)매도호가'])
            first_sell_price = abs(int(first_sell_price))

            first_buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['(최우선)매수호가'])
            first_buy_price = abs(int(first_buy_price))

            if sCode not in self.jango_dict.keys():
                self.jango_dict.update({sCode: {}})

            self.jango_dict[sCode].update({"현재가": current_price})
            self.jango_dict[sCode].update({"종목코드": sCode})
            self.jango_dict[sCode].update({"종목명": stock_name})
            self.jango_dict[sCode].update({"보유수량": stock_quan})
            self.jango_dict[sCode].update({"주문가능수량": like_quan})
            self.jango_dict[sCode].update({"매입단가": buy_price})
            self.jango_dict[sCode].update({"총매입가": total_buy_price})
            self.jango_dict[sCode].update({"매도매수구분": meme_gubun})
            self.jango_dict[sCode].update({"(최우선)매도호가": first_sell_price})
            self.jango_dict[sCode].update({"(최우선)매수호가": first_buy_price})

    def msg_slot(self, sScrNo, sRQName, sTrCode, msg):
        self.logging.logger.debug("스크린: %s, 요청이름: %s, tr코드: %s --- %s" % (sScrNo, sRQName, sTrCode, msg))
        self.myMsg.send_msg_telegram("스크린: %s, 요청이름: %s, tr코드: %s --- %s" % (sScrNo, sRQName, sTrCode, msg))

    def set_real_remove(self):
        for code in self.portfolio_stock_dict.keys():
            self.dynamicCall("SetRealRemove(QString, QString)", self.portfolio_stock_dict[code]['스크린번호'], code)

    def after_market(self):
        self.account_stock_dict = {}
        self.detail_account_mystock()
        message_string = []
        message_string2 = []
        message_string3 = []
        i = 0
        if len(self.account_stock_dict) == 0:
            message_string.append("[보유 종목 없음]")
            self.myMsg.send_msg_telegram('\n'.join(message_string))
        else:
            message_string.append("[보유 종목 리스트]")
            for code in self.account_stock_dict.keys():
                code_name = self.account_stock_dict[code]["종목명"]
                quantity = self.account_stock_dict[code]["보유수량"]
                buy_price = self.account_stock_dict[code]["매입가"]
                current_price = self.account_stock_dict[code]["현재가"]
                profit_rate = self.account_stock_dict[code]["수익률(%)"]
                total_buy_price = quantity * buy_price
                total_current_price = quantity * current_price
                profit = total_current_price - total_buy_price
                if i % 3 == 0:
                    message_string.append(
                        "종목명: %s\n보유수량: %d\n매입가: %d\n현재가: %d\n수익률: %f\n매입금액: %d\n평가금액: %d\n수익: %d" % (
                            code_name, quantity, buy_price, current_price, profit_rate, total_buy_price,
                            total_current_price,
                            profit))
                    message_string.append("-------------------------------------")
                elif i % 3 == 1:
                    message_string3.append(
                        "종목명: %s\n보유수량: %d\n매입가: %d\n현재가: %d\n수익률: %f\n매입금액: %d\n평가금액: %d\n수익: %d" % (
                            code_name, quantity, buy_price, current_price, profit_rate, total_buy_price,
                            total_current_price,
                            profit))
                    message_string3.append("-------------------------------------")
                else:
                    message_string2.append(
                        "종목명: %s\n보유수량: %d\n매입가: %d\n현재가: %d\n수익률: %f\n매입금액: %d\n평가금액: %d\n수익: %d" % (
                            code_name, quantity, buy_price, current_price, profit_rate, total_buy_price,
                            total_current_price,
                            profit))
                    message_string2.append("-------------------------------------")
                i = i + 1
            self.myMsg.send_msg_telegram('\n'.join(message_string))
            self.myMsg.send_msg_telegram('\n'.join(message_string2))
            self.myMsg.send_msg_telegram('\n'.join(message_string3))

        current_holding_list = []
        today = datetime.datetime.today()

        for i in range(30):
            yesterday = (today - timedelta(i)).strftime("%Y%m%d")
            if os.path.exists("files/buy/Module_A_" + yesterday + ".csv"):  # 해당 경로에 파일이 있는지 체크한다.
                f = open("files/buy/Module_A_" + yesterday + ".csv", "r", encoding="utf8")
                csv_data = csv.reader(f)
                next(csv_data)  # csv header skip
                for line in csv_data:  # 줄바꿈된 내용들이 한줄 씩 읽어와진다.
                    if line != "":
                        stock_code = line[8]
                        if stock_code in self.account_stock_dict.keys():
                            current_holding_list.append([stock_code, "A"])
                f.close()

            if os.path.exists("files/buy/Module_B_" + yesterday + ".csv"):  # 해당 경로에 파일이 있는지 체크한다.
                f = open("files/buy/Module_B_" + yesterday + ".csv", "r", encoding="utf8")
                csv_data = csv.reader(f)
                next(csv_data)  # csv header skip
                for line in csv_data:  # 줄바꿈된 내용들이 한줄 씩 읽어와진다.
                    if line != "":
                        stock_code = line[8]
                        if stock_code in self.account_stock_dict.keys():
                            current_holding_list.append([stock_code, "B"])
                f.close()

            if os.path.exists("files/buy/Module_C_" + yesterday + ".csv"):  # 해당 경로에 파일이 있는지 체크한다.
                f = open("files/buy/Module_C_" + yesterday + ".csv", "r", encoding="utf8")
                csv_data = csv.reader(f)
                next(csv_data)  # csv header skip
                for line in csv_data:  # 줄바꿈된 내용들이 한줄 씩 읽어와진다.
                    if line != "":
                        stock_code = line[8]
                        if stock_code in self.account_stock_dict.keys():
                            current_holding_list.append([stock_code, "C"])
                f.close()

        df = pd.DataFrame(current_holding_list, columns=['Code', 'Logic'])
        df = df.drop_duplicates(subset=None, keep='first', inplace=False, ignore_index=False)
        df.to_csv('files/hold/holding_list_' + today.strftime("%Y%m%d") + '.csv', index=False)

    def buy_list_process(self):
        self.logging.logger.debug("매수/매도 후보 추출 프로세스 시작")
        self.myMsg.send_msg_telegram("매수/매도 후보 추출 프로세스 시작")

        analysis.checkBuySellList.check_buy_sell_list()

        self.logging.logger.debug("매수/매도 후보 추출 프로세스 완료")
        self.myMsg.send_msg_telegram("매수/매도 후보 추출 프로세스 완료")

        sys.exit(1)
