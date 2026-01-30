#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 讲座抢票自动化脚本 - 使用Playwright自动填写问卷星报名表
# 分支测试
import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

class TicketGrabber:
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.user = self.config['user_info']
        self.settings = self.config['settings']
        
    def wait_for_start_time(self):
        """等待开始时间"""
        if not self.settings['wait_before_start']:
            return False
        start_time = datetime.strptime(self.settings['start_time'], '%Y-%m-%d %H:%M:%S')
        while datetime.now() < start_time:
            remaining = (start_time - datetime.now()).total_seconds()
            print(f"等待开始时间，剩余 {int(remaining)} 秒...")
            time.sleep(0.5)
        print("🚀 开始时间到，立即执行抢票！")
        return True
    
    def wait_for_form_ready(self, page):
        """循环检测表单是否就绪（用于定时抢票）"""
        max_wait = self.settings.get('form_check_timeout', 60)  # 默认60秒
        print(f"正在检测表单是否开放（最多等待{max_wait}秒）...")
        start = time.time()
        attempt = 0
        while time.time() - start < max_wait:
            attempt += 1
            try:
                # 检查姓名输入框是否可见且可用
                name_input = page.locator('input[name="q1"]')
                if name_input.count() > 0 and name_input.is_visible():
                    print(f"✓ 表单已开放！（尝试{attempt}次，耗时{time.time()-start:.1f}秒）")
                    return True
                # 每0.5秒刷新一次页面重新检测
                if attempt % 2 == 0:  # 每秒刷新一次
                    page.reload(wait_until='domcontentloaded')
                    print(f"  第{attempt//2}次刷新页面检测...")
                time.sleep(0.5)
            except Exception as e:
                time.sleep(0.5)
                continue
        print(f"✗ 表单未在{max_wait}秒内开放，可能报名时间有变化")
        return False
    
    def fill_form(self, page):
        """填写表单"""
        try:
            # 姓名（使用精确的name属性定位）
            page.locator('input[name="q1"]').fill(self.user['name'])
            print(f"✓ 已填写姓名: {self.user['name']}")
            time.sleep(0.3)  # 短暂等待确保填写完成
            
            # 学院选择（使用文本匹配更可靠）
            page.get_by_text(self.user['college'], exact=True).click()
            print(f"✓ 已选择学院: {self.user['college']}")
            time.sleep(0.3)
            
            # 学号（使用精确的name属性定位）
            page.locator('input[name="q3"]').fill(self.user['student_id'])
            print(f"✓ 已填写学号: {self.user['student_id']}")
            time.sleep(0.3)
            
            # 电话（使用精确的name属性定位）
            page.locator('input[name="q4"]').fill(self.user['phone'])
            print(f"✓ 已填写电话: {self.user['phone']}")
            time.sleep(0.3)
            
            # 勾选协议
            if self.settings['auto_agree_terms']:
                checkbox = page.locator('input[type="checkbox"]')
                if not checkbox.is_checked():
                    checkbox.check()
                print("✓ 已勾选用户协议")
                time.sleep(0.2)
            
            return True
        except Exception as e:
            print(f"✗ 填写表单失败: {e}")
            import traceback
            traceback.print_exc()  # 打印详细错误信息便于调试
            return False
    
    def submit_form(self, page):
        """提交表单"""
        try:
            submit_btn = page.locator('div.ui-btn:has-text("提交")')
            submit_btn.click()
            print("✓ 表单已提交！")
            time.sleep(2)
            return True
        except Exception as e:
            print(f"✗ 提交失败: {e}")
            return False
    
    def run(self):
        """主执行流程"""
        print("=" * 50)
        print("讲座抢票脚本启动")
        print("=" * 50)
        
        is_timed = self.settings['wait_before_start']
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.settings['headless'])
            context = browser.new_context()
            page = context.new_page()
            
            try:
                if is_timed:
                    # 定时模式：提前打开页面准备
                    print(f"⏰ 定时模式启动")
                    print(f"📍 提前访问页面进行准备...")
                    page.goto(self.settings['target_url'], wait_until='domcontentloaded')
                    print(f"✓ 页面已打开，准备就绪")
                    
                    # 等待开始时间
                    self.wait_for_start_time()
                    
                    # 循环检测表单是否开放
                    if not self.wait_for_form_ready(page):
                        print("⚠️  表单长时间未开放，但继续尝试填写...")
                else:
                    # 立即模式：直接访问并等待表单
                    print(f"⚡ 立即执行模式")
                    print(f"正在访问: {self.settings['target_url']}")
                    page.goto(self.settings['target_url'], wait_until='networkidle')
                    print("✓ 页面加载完成")
                    
                    # 等待表单就绪
                    try:
                        page.wait_for_selector('input[name="q1"]', timeout=10000)
                        print("✓ 表单已就绪")
                    except:
                        print("⚠️  表单加载较慢，继续尝试...")
                
                # 填写并提交表单
                if self.fill_form(page):
                    if self.submit_form(page):
                        print("\n" + "=" * 50)
                        print("🎉 抢票成功！所有信息已提交。")
                        print("=" * 50)
                    else:
                        print("\n❌ 提交失败，请检查网络或手动提交。")
                else:
                    print("\n❌ 填写失败，请检查配置文件或页面状态。")
                
                input("\n按回车键关闭浏览器...")
                
            except PlaywrightTimeout:
                print("✗ 页面加载超时，请检查网络连接")
            except Exception as e:
                print(f"✗ 执行出错: {e}")
                import traceback
                traceback.print_exc()
            finally:
                browser.close()

if __name__ == '__main__':
    grabber = TicketGrabber()
    grabber.run()

