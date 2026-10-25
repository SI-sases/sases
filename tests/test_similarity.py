import os
import sys
import pytest

# 确保可以导入 core 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import similarity

def test_identical_strings_are_similar():
    desc = "写一个Python函数，判断一个整数是否是质数"
    existing = [desc]
    assert similarity.is_similar(desc, existing, threshold=0.30) is True

def test_semantically_similar_chinese_strings():
    desc_a = "写一个Python函数，计算一个整数列表中所有元素的平均值"
    desc_b = "写一个Python函数，返回给定数字列表的平均数"
    existing = [desc_a]
    assert similarity.is_similar(desc_b, existing, threshold=0.30) is True

def test_dissimilar_strings_are_not_similar():
    desc_a = "现有一个长度为n的整数数组，请设计一个时间复杂度为O(n log n)的排序算法并分析其空间复杂度"
    desc_b = "给定两个字符串，判断它们是否互为字母异位词，并考虑Unicode字符的处理"
    existing = [desc_a]
    assert similarity.is_similar(desc_b, existing, threshold=0.30) is False

def test_empty_existing_returns_false():
    assert similarity.is_similar("任意任务", [], threshold=0.30) is False
