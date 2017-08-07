/*
    This file is part of Bard.

    Bard is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/

#include <boost/python/module.hpp>
#include <boost/python/def.hpp>
#include <boost/python/extract.hpp>
#include <boost/python/stl_iterator.hpp>
#include <boost/python/list.hpp>
#include <boost/python/tuple.hpp>
#include <boost/python/class.hpp>
#include <vector>
#include <map>
#include <iostream>

template<typename T>
inline
std::vector<T> to_std_vector( const boost::python::object& iterable )
{
    return std::vector<T>( boost::python::stl_input_iterator<T>( iterable ),
                           boost::python::stl_input_iterator<T>( ) );
}

template<typename T>
long greet(boost::python::list &a)
{
   auto v = to_std_vector<int>(a);
   return v[0];
}

boost::python::tuple greet2()
{
   int i1=-1442137496;
   int i2=1786980374;
   int a=__builtin_popcount(i1 ^ i2);
   return boost::python::make_tuple(a,2,3);
}

class FingerprintManager
{
public:
    FingerprintManager();
    void setMaxOffset(int maxoffset);
    int maxOffset() const;

    void addSong(long songID, boost::python::list &fingerprint);
    boost::python::list addSongAndCompare(long songID, boost::python::list &fingerprint, double cancelThreshold=0.55);
    long compareSongs(long songID1, long songID2, int maxoffset=50, double cancelThreshold=0.55);
    std::pair<int, double> compareChromaprintFingerprintsAndOffset(std::vector<int> fp1, std::vector<int> fp2, double cancelThreshold) const;

private:
    int m_maxoffset;
    std::map<int, std::vector<int> > m_fingerprints;
};

FingerprintManager::FingerprintManager(): m_maxoffset(50)
{
}


void FingerprintManager::setMaxOffset(int maxoffset)
{
    m_maxoffset = maxoffset;
}

int FingerprintManager::maxOffset() const
{
    return m_maxoffset;
}

void FingerprintManager::addSong(long songID, boost::python::list &fingerprint)
{
    auto v = to_std_vector<int>(fingerprint);
    v.insert(v.begin(), m_maxoffset, 0);
    m_fingerprints[songID]=v;
}

boost::python::list FingerprintManager::addSongAndCompare(long songID, boost::python::list &fingerprint, double cancelThreshold)
{
    boost::python::list result;
    auto v = to_std_vector<int>(fingerprint);
//    std::cout << "len: " << v.size() << std::endl;
    v.insert(v.begin(), m_maxoffset, 0);
//    std::cout << "new len: " << v.size() << std::endl;
    for (auto & [itSongID, itFingerprint]: m_fingerprints)
    {
        auto [offset, similarity] = compareChromaprintFingerprintsAndOffset(itFingerprint, v, cancelThreshold);
        if (similarity > cancelThreshold)
        {
//            std::cout << "****" << songID << " " << itSongID << " " << offset << " " << similarity << std::endl;
            result.append(boost::python::make_tuple(itSongID, offset, similarity));
        } /*else {
            if (similarity < 0 )
                std::cout << songID << " " << itSongID << " different" << std::endl;
            else
                std::cout << songID << " " << itSongID << " " << offset << " " << similarity << std::endl;
        }*/

    }

    m_fingerprints[songID]=v;
    return result;
}

std::pair<int, double> FingerprintManager::compareChromaprintFingerprintsAndOffset(std::vector<int> fp1, std::vector<int> fp2, double cancelThreshold) const
{
    std::vector<int>::const_iterator it1, it2;
    int offset;
    int total_idx;
    int remaining;
    int threshold_bits;
    int equal_bits, total_bits;
    int i;
    double best_result = -1;
    int best_offset = -1;
    bool ok;
    for (offset=0; offset < m_maxoffset; ++offset)
    {
//        std::cout << "offset " << offset << "----------" << std::endl;
        it1 = fp1.cbegin() + (m_maxoffset - offset);
        it2 = fp2.cbegin() + m_maxoffset;
        ok = true;
        equal_bits = 0;
        total_idx = std::min(fp1.size()-m_maxoffset+offset, fp2.size()-m_maxoffset);
//        std::cout << "total_idx " << total_idx << std::endl;
        remaining = total_bits = total_idx * 32;
        threshold_bits = total_bits * cancelThreshold;
//        std::cout << "threshold " << threshold_bits << std::endl;
        int idx=0;
        for (; it1!=fp1.end() && it2!=fp2.end() ; ++it1, ++it2, ++idx)
        {
//            std::cout << "(" << (idx-offset) << ") " << *it1 << " (" << idx << ") " << *it2 << std::endl;
            equal_bits += 32 - __builtin_popcount(*it1 ^ *it2);
            remaining -= 32;
//            std::cout << "equal_bits " << equal_bits << "  remaining " << remaining << " threshold_bits " << threshold_bits << std::endl;
            if (equal_bits + remaining < threshold_bits)
            {
                ok = false;
//                std::cout << "break" << *it2 << std::endl;
                break;
            }
        }
       if (ok)
       {
           double result = equal_bits/(double)total_bits;
           if (result > best_result)
           {
               best_result = result;
               best_offset = offset;
           }
       }
    }
    for (offset=1; offset < m_maxoffset; ++offset)
    {
//        std::cout << "offset " << offset << "----------" << std::endl;
        it1 = fp1.cbegin() + m_maxoffset;
        it2 = fp2.cbegin() + (m_maxoffset - offset);
        ok = true;
        equal_bits = 0;
        total_idx = std::min(fp1.size()-m_maxoffset, fp2.size()-m_maxoffset+offset);
//        std::cout << "total_idx " << total_idx << std::endl;
        remaining = total_bits = total_idx * 32;
        threshold_bits = total_bits * cancelThreshold;
//        std::cout << "threshold " << threshold_bits << std::endl;
        int idx = 0;
        for (; it1!=fp1.end() && it2!=fp2.end() ; ++it1, ++it2, ++idx)
        {
//            std::cout << "(" << (idx) << ") " << *it1 << " (" << idx-offset << ") " << *it2 << std::endl;
            equal_bits += 32 - __builtin_popcount(*it1 ^ *it2);
            remaining -= 32;
//            std::cout << "equal_bits " << equal_bits << "  remaining " << remaining << " threshold_bits " << threshold_bits << std::endl;
            if (equal_bits + remaining < threshold_bits)
            {
                ok = false;
//                std::cout << "break" << *it2 << std::endl;
                break;
            }
        }
        if (ok)
        {
            double result = equal_bits/(double)total_bits;
            if (result > best_result)
            {
                best_result = result;
                best_offset = -offset;
            }
        }
    }
    return std::make_pair(best_offset, best_result);
}

long FingerprintManager::compareSongs(long songID1, long songID2, int maxoffset, double cancelThreshold)
{
    return m_fingerprints[songID1][0];
}

BOOST_PYTHON_MODULE(bard_ext)
{
    using namespace boost::python;
    def("greet", greet<int>);
    def("greet2", greet2);
    class_<FingerprintManager>("FingerprintManager")
        .def("addSong", &FingerprintManager::addSong)
        .def("addSongAndCompare", &FingerprintManager::addSongAndCompare)
        .def("compareSongs", &FingerprintManager::compareSongs)
        .def("setMaxOffset", &FingerprintManager::setMaxOffset)
        .def("maxOffset", &FingerprintManager::maxOffset);
}


