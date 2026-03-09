/**
 * OpenFHE Evaluation Key Dump
 *
 * Dumps RelinKeys and Galois/Rotation keys to the project schema.
 * See PROJECT_ARCHITECTURE.md §7. Schema matches SEAL dump for distinguisher compatibility.
 *
 * Usage: ./openfhe_dump_keys --output <path> [--poly_modulus 4096] [--scheme ckks]
 *
 * Requires: OpenFHE v1.4.x (built with MinGW64 or GCC)
 */

#include "openfhe.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <filesystem>
#include <chrono>
#include <iomanip>
#include <ctime>

namespace fs = std::filesystem;
using namespace lbcrypto;

struct DumpConfig {
  std::string output_path;
  std::size_t poly_modulus = 4096;
  std::string scheme = "ckks";
};

// Write metadata.json
void write_metadata(const std::string& path,
                   const std::vector<uint64_t>& primes,
                   std::size_t N, std::size_t relin_blocks,
                   std::size_t galois_count, bool in_ntt) {
  std::ofstream f(path + "/metadata.json");
  if (!f) {
    throw std::runtime_error("Cannot write metadata.json");
  }
  auto now = std::chrono::system_clock::now();
  auto t = std::chrono::system_clock::to_time_t(now);
  std::tm tm_buf;
#ifdef _WIN32
  localtime_s(&tm_buf, &t);
#else
  localtime_r(&t, &tm_buf);
#endif
  std::ostringstream ts;
  ts << std::put_time(&tm_buf, "%Y-%m-%dT%H:%M:%S");

  f << "{\n"
    << "  \"library\": \"openfhe\",\n"
    << "  \"version\": \"1.4.2\",\n"
    << "  \"N\": " << N << ",\n"
    << "  \"primes\": [";
  for (std::size_t i = 0; i < primes.size(); ++i) {
    f << primes[i];
    if (i + 1 < primes.size()) f << ", ";
  }
  f << "],\n"
    << "  \"relin_blocks\": " << relin_blocks << ",\n"
    << "  \"rotation_count\": " << galois_count << ",\n"
    << "  \"timestamp\": \"" << ts.str() << "\",\n"
    << "  \"in_ntt_domain\": " << (in_ntt ? "true" : "false") << "\n"
    << "}\n";
}

// Dump one DCRTPoly's coefficients per RNS prime to binary files
void dump_dcrtpoly_prime(const DCRTPoly& poly, std::size_t prime_index,
                         std::size_t N, const std::string& filepath) {
  const auto& elements = poly.GetAllElements();
  if (prime_index >= elements.size()) return;

  const auto& tower = elements[prime_index];
  std::ofstream f(filepath, std::ios::binary);
  if (!f) return;

  std::size_t len = tower.GetLength();
  for (std::size_t i = 0; i < len && i < N; ++i) {
    uint64_t val = tower[i].ConvertToInt();
    f.write(reinterpret_cast<const char*>(&val), sizeof(uint64_t));
  }
  // Pad to N if needed
  for (std::size_t i = len; i < N; ++i) {
    uint64_t zero = 0;
    f.write(reinterpret_cast<const char*>(&zero), sizeof(uint64_t));
  }
}

// Dump RelinKeys (EvalMultKey)
void dump_relin_keys(const std::vector<EvalKey<DCRTPoly>>& eval_mult_keys,
                     const std::string& base_path,
                     std::vector<uint64_t>& primes, std::size_t& N, bool& in_ntt) {
  if (eval_mult_keys.empty()) {
    std::cerr << "No relinearization keys found.\n";
    return;
  }

  auto relin_key = std::dynamic_pointer_cast<EvalKeyRelinImpl<DCRTPoly>>(eval_mult_keys[0]);
  if (!relin_key || !(*relin_key)) {
    std::cerr << "RelinKey cast failed.\n";
    return;
  }

  const auto& a_vec = relin_key->GetAVector();
  const auto& b_vec = relin_key->GetBVector();
  if (a_vec.empty() || b_vec.empty()) return;

  // Get N and primes from first element
  const DCRTPoly& first = a_vec[0];
  N = first.GetRingDimension();
  const auto& params = first.GetParams();
  if (!params) return;

  primes.clear();
  for (const auto& p : params->GetParams()) {
    primes.push_back(p->GetModulus().ConvertToInt());
  }

  in_ntt = (first.GetFormat() == Format::EVALUATION);

  std::string level_dir = base_path + "/relin/level_0";
  fs::create_directories(level_dir);

  std::size_t num_blocks = std::min(a_vec.size(), b_vec.size());
  for (std::size_t block = 0; block < num_blocks; ++block) {
    for (std::size_t p = 0; p < primes.size(); ++p) {
      std::ostringstream fn0, fn1;
      fn0 << level_dir << "/block_" << block << "_prime_" << p << "_ksk0.bin";
      fn1 << level_dir << "/block_" << block << "_prime_" << p << "_ksk1.bin";
      dump_dcrtpoly_prime(a_vec[block], p, N, fn0.str());
      dump_dcrtpoly_prime(b_vec[block], p, N, fn1.str());
    }
  }
}

// Dump rotation keys (EvalSumKey / EvalAutomorphismKey)
void dump_rotation_keys(const std::map<uint32_t, EvalKey<DCRTPoly>>& eval_sum_map,
                       const std::string& base_path,
                       const std::vector<uint64_t>& primes, std::size_t N) {
  for (const auto& kv : eval_sum_map) {
    uint32_t automorphism_idx = kv.first;
    auto eval_key = std::dynamic_pointer_cast<EvalKeyRelinImpl<DCRTPoly>>(kv.second);
    if (!eval_key || !(*eval_key)) continue;

    const auto& a_vec = eval_key->GetAVector();
    const auto& b_vec = eval_key->GetBVector();
    if (a_vec.empty() || b_vec.empty()) continue;

    std::ostringstream dir;
    dir << base_path << "/rotation/automorphism_" << automorphism_idx << "/level_0";
    fs::create_directories(dir.str());

    std::size_t num_blocks = std::min(a_vec.size(), b_vec.size());
    for (std::size_t block = 0; block < num_blocks; ++block) {
      for (std::size_t p = 0; p < primes.size(); ++p) {
        std::ostringstream fn0, fn1;
        fn0 << dir.str() << "/block_" << block << "_prime_" << p << "_ksk0.bin";
        fn1 << dir.str() << "/block_" << block << "_prime_" << p << "_ksk1.bin";
        dump_dcrtpoly_prime(a_vec[block], p, N, fn0.str());
        dump_dcrtpoly_prime(b_vec[block], p, N, fn1.str());
      }
    }
  }
}

int main(int argc, char* argv[]) {
  DumpConfig cfg;
  cfg.output_path = "dump_out";

  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "--output" && i + 1 < argc) {
      cfg.output_path = argv[++i];
    } else if (arg == "--poly_modulus" && i + 1 < argc) {
      cfg.poly_modulus = static_cast<std::size_t>(std::stoull(argv[++i]));
    } else if (arg == "--scheme" && i + 1 < argc) {
      cfg.scheme = argv[++i];
    }
  }

  try {
    CCParams<CryptoContextCKKSRNS> parameters;
    parameters.SetMultiplicativeDepth(5);
    parameters.SetScalingModSize(50);
    parameters.SetScalingTechnique(FLEXIBLEAUTO);
    parameters.SetBatchSize(static_cast<uint32_t>(cfg.poly_modulus / 2));  // slots = N/2

    CryptoContext<DCRTPoly> cc = GenCryptoContext(parameters);
    cc->Enable(PKE);
    cc->Enable(KEYSWITCH);
    cc->Enable(LEVELEDSHE);
    cc->Enable(ADVANCEDSHE);

    auto keys = cc->KeyGen();
    cc->EvalMultKeyGen(keys.secretKey);

    try {
      cc->EvalSumKeyGen(keys.secretKey, keys.publicKey);
    } catch (const std::exception& e) {
      std::cerr << "Note: EvalSumKeyGen failed: " << e.what() << "\n";
    }

    std::string key_tag = keys.secretKey->GetKeyTag();
    const auto& eval_mult_vec = cc->GetEvalMultKeyVector(key_tag);
    const auto& eval_sum_map = cc->GetEvalAutomorphismKeyMap(key_tag);

    std::vector<uint64_t> primes;
    std::size_t N = 0;
    bool in_ntt = false;

    fs::create_directories(cfg.output_path);
    fs::create_directories(cfg.output_path + "/relin/level_0");

    dump_relin_keys(eval_mult_vec, cfg.output_path, primes, N, in_ntt);

    std::size_t relin_blocks = eval_mult_vec.empty() ? 0 : 1;
    if (!eval_mult_vec.empty()) {
      auto rk = std::dynamic_pointer_cast<EvalKeyRelinImpl<DCRTPoly>>(eval_mult_vec[0]);
      if (rk) relin_blocks = rk->GetAVector().size();
    }

    std::size_t galois_count = eval_sum_map.size();

    write_metadata(cfg.output_path, primes, N, relin_blocks, galois_count, in_ntt);

    dump_rotation_keys(eval_sum_map, cfg.output_path, primes, N);

    std::cout << "OpenFHE dump_keys\n";
    std::cout << "Output: " << cfg.output_path << "\n";
    std::cout << "N: " << N << ", scheme: " << cfg.scheme << "\n";
    std::cout << "Relin blocks: " << relin_blocks << ", Rotation keys: " << galois_count << "\n";
    std::cout << "Primes: " << primes.size() << "\n";
    std::cout << "Done.\n";

  } catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << "\n";
    return 1;
  }

  return 0;
}
